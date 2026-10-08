"""Live-site adapters for clean captures; no recognition or synthetic artwork."""

import re
from urllib.parse import urlencode

from tools.capture_batch import check_png
from tools.capture_lichess import expand_placement


SNAPSHOT = r"""async (board, platform) => {
 const rect = board.getBoundingClientRect();
 const bounds = {x:rect.x,y:rect.y,width:rect.width,height:rect.height};
 const rows = Array.from({length:8},()=>Array(8).fill('.'));
 const urls = e => {
   const found = [];
   for (const pseudo of [null, '::before', '::after']) {
     const style = getComputedStyle(e,pseudo);
     for (const match of style.backgroundImage.matchAll(/url\(["']?(.*?)["']?\)/g))
       found.push(new URL(match[1],document.baseURI).href);
   }
   return [...new Set(found)];
 };
 const visible = e => {
   const s = getComputedStyle(e), r=e.getBoundingClientRect();
   return s.display!=='none' && s.visibility==='visible' && Number(s.opacity)>0 && r.width>0 && r.height>0;
 };
 if (!visible(board)) throw Error('Board is not visible');
 const pieces = [], roles={pawn:'p',knight:'n',bishop:'b',rook:'r',queen:'q',king:'k'};
 for (const e of board.querySelectorAll(platform==='lichess'?'piece':'.piece')) {
   if (!visible(e)) throw Error('Hidden piece');
   let code;
   if (platform==='lichess') {
     const role=Object.keys(roles).find(k=>e.classList.contains(k));
     if (!role || (!e.classList.contains('white') && !e.classList.contains('black'))) throw Error('Unknown piece');
     code=(e.classList.contains('white')?'w':'b')+roles[role];
   } else code=[...e.classList].find(c=>/^[wb][pnbrqk]$/.test(c));
   if (!code) throw Error('Unknown piece');
   const r=e.getBoundingClientRect(), x=(r.x-rect.x)/(rect.width/8), y=(r.y-rect.y)/(rect.height/8);
   const col=Math.round(x), row=Math.round(y);
   if (col<0||col>7||row<0||row>7||Math.abs(x-col)>.025||Math.abs(y-row)>.025||
       Math.abs(r.width-rect.width/8)>1 || Math.abs(r.height-rect.height/8)>1 || rows[row][col]!=='.')
     throw Error('Moving, overlapping or misplaced pieces');
   rows[row][col]=code[0]==='w'?code[1].toUpperCase():code[1];
   const artwork=urls(e);
   if (!artwork.length) throw Error('Missing piece artwork');
   pieces.push({code,artwork});
 }
 // Check every square, including its corners, for covering dialogs or menus.
 for (let r=0;r<8;r++) for(let c=0;c<8;c++) for(const dx of [.15,.5,.85]) for(const dy of [.15,.5,.85]) {
   const hit=document.elementFromPoint(rect.x+(c+dx)*rect.width/8,rect.y+(r+dy)*rect.height/8);
   if (!hit || !(hit===board || board.contains(hit))) throw Error('Board is covered or outside viewport');
 }
 const overlays = platform==='lichess'
   ? [...board.querySelectorAll('square'), ...board.parentElement.querySelectorAll('svg g > *')]
   : [...board.querySelectorAll('.highlight,.arrow,.annotation,.badge'),
      ...board.querySelectorAll('.arrows path,.arrows polygon,.arrows line')];
 if (overlays.some(visible)) throw Error('Visible markings on a clean board');
 if (board.getAnimations({subtree:true}).some(a=>a.playState==='running')) throw Error('Animated board');
 const boardArtwork=urls(board);
 const all=[...new Set([...boardArtwork,...pieces.flatMap(p=>p.artwork)])];
 await document.fonts.ready;
 await Promise.all(all.map(url=>new Promise((resolve,reject)=>{
   const image=new Image(), timer=setTimeout(()=>reject(Error('Artwork timed out')),10000);
   image.onload=()=>{clearTimeout(timer);resolve();};
   image.onerror=()=>{clearTimeout(timer);reject(Error('Artwork failed to load'));};image.src=url;
 })));
 let style, orientation;
 if(platform==='lichess') {
   style={board:document.body.dataset.board,pieces:document.body.dataset.pieceSet,
          is3d:document.body.classList.contains('is3d')};
   orientation=board.closest('.cg-wrap').classList.contains('orientation-black')?'black-bottom':'white-bottom';
 } else {
   style=board.game.getOptions().themeAssets;
   orientation=board.state.isFlipped?'black-bottom':'white-bottom';
 }
 return {bounds,rows:rows.map(r=>r.join('')),pieces,boardArtwork,style,orientation};
}"""


def dismiss_dialogs(page):
    for selector in ('button[aria-label="Close"]', '#onetrust-reject-all-handler'):
        locator = page.locator(selector)
        if locator.count() and locator.first.is_visible():
            locator.first.evaluate("e => e.click()")


def select_lichess(page, config):
    for field, menu, choice in (("board", "Board", config["boardTheme"]),
                                 ("pieceSet", "Piece set", config["pieceSet"])):
        if page.locator("body").get_attribute("data-board" if field == "board" else "data-piece-set") == choice:
            continue
        page.locator(".dasher .toggle").click()
        page.locator("#dasher_app button.sub").filter(has_text=re.compile(f"^{menu}$", re.I)).click()
        option = page.locator(f'#dasher_app button[title="{choice}"]')
        if not option.count():
            page.locator("#dasher_app").get_by_role("button", name=re.compile("more", re.I)).click()
        option.click()
        page.wait_for_function("([field,value])=>document.body.dataset[field]===value", arg=[field, choice])
        page.locator("#dasher_app button.head").click()
        page.locator(".dasher .toggle").click()
    return page.evaluate("""({boardTheme,pieceSet}) => {
      const boardName=({canvas:'canvas2',pink:'pink-pyramid'})[boardTheme] || boardTheme;
      const candidates=['png','jpg','svg'].map(ext=>`images/board/${boardName}.${ext}`);
      candidates.push(`images/board/svg/${boardName}.svg`);
      const boardPath=candidates.find(p=>site.manifest.hashed[p]);
      if(!boardPath) throw Error('Board asset not found in site manifest');
      const pieces={};
      for(const color of ['w','b']) for(const role of ['P','N','B','R','Q','K']) {
        const base=`piece/${pieceSet}/${color}${role}`;
        const path=['webp','svg'].map(ext=>`${base}.${ext}`).find(p=>site.manifest.hashed[p]);
        if(!path) throw Error('Piece asset not found in site manifest');
        pieces[color+role.toLowerCase()]=new URL(site.asset.url(path),document.baseURI).href;
      }
      return {board:new URL(site.asset.url(boardPath),document.baseURI).href,pieces};
    }""", {"boardTheme": config["boardTheme"], "pieceSet": config["pieceSet"]})


def chesscom_assets(catalogue, config):
    """Resolve only public, unlocked, top-down web artwork from the site catalogue."""
    chosen = {}
    for collection, field, requested in (
        ("boardStyles", "boardStyle", config["boardTheme"]),
        ("pieceSets", "pieceSet", config["pieceSet"]),
    ):
        matches = [entry for entry in catalogue[collection]
                   if re.sub(r"[ _]+", "-", entry[field]["name"].lower()) == requested]
        if len(matches) != 1 or matches[0].get("isUnlocked") is not True:
            raise ValueError(f"Requested public style is unavailable: {requested}")
        item = matches[0][field]
        if "PLATFORM_WEB" not in item["supportedPlatforms"]:
            raise ValueError("Style does not support web")
        chosen[field] = item
    board, pieces = chosen["boardStyle"], chosen["pieceSet"]
    if pieces["perspective"] != "PIECE_PERSPECTIVE_TOP_DOWN":
        raise ValueError("Only top-down 2D pieces are supported")
    assets = {}
    for color, name in (("w", "white"), ("b", "black")):
        for role, full in (("p", "Pawn"), ("n", "Knight"), ("b", "Bishop"),
                           ("r", "Rook"), ("q", "Queen"), ("k", "King")):
            assets[color + role] = pieces["images"][name + full]
    urls = [board["image"], *assets.values()]
    if any(not isinstance(url, str) or not url.startswith("https://") for url in urls):
        raise ValueError("Missing or invalid public artwork URL")
    return {
        "board": {"assets": {"background": board["image"]}, "config": {
            "highlightSquareHex": board["highlightColor"],
            "darkSquareCoordinateHex": board["coordinateColorLight"],
            "lightSquareCoordinateHex": board["coordinateColorDark"]}},
        "pieces": {"assets": assets},
        "config": {"perspective": "TOP_DOWN"},
    }, {key: {"id": item["id"], "name": item["name"], "isUnlocked": True}
        for key, item in chosen.items()}


def select_chesscom(page, board, config):
    # Reading the public catalogue does not change account preferences. Anonymous
    # preference saves can fail silently, so configure the local board renderer.
    with page.expect_response(lambda r: r.url.endswith("/ListThemesSelection") and r.ok) as response:
        page.locator('button[aria-label="Settings"]').first.click()
        page.get_by_text("Board", exact=True).click()
    catalogue = response.value.json()
    assets, choices = chesscom_assets(catalogue, config)
    dismiss_dialogs(page)
    expected = board.evaluate("""(e, assets) => {
      const theme = {...e.game.getOptions().themeAssets, ...assets};
      e.game.setOptions({themeAssets: theme});
      return theme;
    }""", assets)
    choices["method"] = "local-board-options"
    choices["catalogueUrl"] = response.value.url
    return expected, choices


def verify_snapshot(snapshot, placement, config, view, expected_style=None):
    rows = expand_placement(placement)
    if view == "black-bottom":
        rows = [row[::-1] for row in rows[::-1]]
    if snapshot["rows"] != rows or snapshot["orientation"] != view:
        raise ValueError("Rendered position or orientation differs from the requested label")
    if config["platform"] == "lichess":
        if snapshot["style"] != {"board": config["boardTheme"], "pieces": config["pieceSet"], "is3d": False}:
            raise ValueError("Rendered lichess style differs from request")
        for piece in snapshot["pieces"]:
            if not expected_style or piece["artwork"] != [expected_style["pieces"][piece["code"]]]:
                raise ValueError("Actual piece artwork disagrees with lichess style or role")
        if not expected_style or snapshot["boardArtwork"] != [expected_style["board"]]:
            raise ValueError("Actual board artwork disagrees with lichess theme")
    else:
        if not expected_style or snapshot["style"] != expected_style:
            raise ValueError("Chess.com style changed after selection")
        if snapshot["boardArtwork"] != [expected_style["board"]["assets"]["background"]]:
            raise ValueError("Chess.com board pixels use a different artwork source")
        for piece in snapshot["pieces"]:
            if piece["artwork"] != [expected_style["pieces"]["assets"][piece["code"]]]:
                raise ValueError("Chess.com piece pixels use a different artwork source")


def capture_page(page, placement, config, view):
    platform = config["platform"]
    if platform == "lichess":
        url = "https://lichess.org/editor?" + urlencode({"fen": placement, "color": view.split("-")[0]})
        selector = ".main-board cg-board"
    else:
        url = "https://www.chess.com/analysis?" + urlencode({"fen": placement})
        selector = "wc-chess-board"
    response = page.goto(url, wait_until="domcontentloaded")
    if response is None or not response.ok:
        raise ValueError("Platform page could not be loaded")
    board = page.locator(selector)
    board.wait_for(state="visible")
    expected_style, choices = None, None
    if platform == "lichess":
        expected_style = select_lichess(page, config)
        modifications = ".copyables, cg-resize { visibility:hidden !important; }"
        description = "FEN/URL answer fields and resize handle hidden; native style selectors used"
    else:
        page.wait_for_timeout(2000)
        dismiss_dialogs(page)
        expected_style, choices = select_chesscom(page, board, config)
        if board.evaluate("e=>Boolean(e.state.isFlipped)") != (view == "black-bottom"):
            page.locator('[aria-label="Flip Board"]').evaluate("e => e.click()")
        page.wait_for_function("([b,v])=>Boolean(b.state.isFlipped)===v",
                               arg=[board.element_handle(), view == "black-bottom"])
        modifications = ".arrows,.highlight,.element-pool,.evaluation-bar,textarea,input { visibility:hidden !important; }"
        description = "Onboarding dismissed, cookies rejected when shown; arrows/highlights/evaluation bar/answer inputs hidden; public unlocked catalogue artwork applied to local board options"
    page.add_style_tag(content=modifications)
    page.mouse.move(0, 0)
    page.wait_for_timeout(400)
    before = board.evaluate(SNAPSHOT, platform)
    verify_snapshot(before, placement, config, view, expected_style)
    png = page.screenshot(type="png", animations="disabled", full_page=False, scale="device")
    after = board.evaluate(SNAPSHOT, platform)
    verify_snapshot(after, placement, config, view, expected_style)
    if before != after:
        raise ValueError("Board geometry, artwork or labels changed during screenshot")
    factor = config["deviceScaleFactor"]
    bounds = {key: value * factor for key, value in before["bounds"].items()}
    size = check_png(png, bounds, (config["viewport"]["width"] * factor, config["viewport"]["height"] * factor))
    return png, {"boardBounds": bounds, "imageSize": size,
                 "verification": "DOM pieces, computed artwork, orientation and geometry checked before/after screenshot",
                 "source": {"url": url, "client": "desktop-web", "locale": "en-GB",
                            "layoutId": "LC01" if platform == "lichess" else "CC01",
                            "pageModification": description, "cssBoardBounds": before["bounds"],
                            "selectorChoices": choices, "observedStyle": before["style"],
                            "boardArtwork": before["boardArtwork"], "pieceArtwork": before["pieces"]}}

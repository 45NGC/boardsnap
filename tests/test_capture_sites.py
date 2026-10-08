"""Offline DOM fixtures exercise screenshot checks, never recognition accuracy."""

from copy import deepcopy
import os

import pytest

from tools import capture_sites as sites
from tools.capture_batch import check_png


PLACEMENT = "R7/8/8/8/8/8/8/7k"
CONFIG = {"id": "test", "platform": "lichess", "boardTheme": "green", "pieceSet": "merida",
          "orientations": ["white-bottom", "black-bottom"], "viewport": {"width": 1024, "height": 900},
          "deviceScaleFactor": 1, "conditions": ["clean"]}


@pytest.fixture
def browser():
    if os.environ.get("BOARDSNAP_BROWSER_TESTS") != "1":
        pytest.skip("Set BOARDSNAP_BROWSER_TESTS=1 to run offline Chromium tests")
    api = pytest.importorskip("playwright.sync_api")
    with api.sync_playwright() as p:
        engine = p.chromium.launch()
        try:
            yield engine
        finally:
            engine.close()


def html(view, platform="lichess", fault=None):
    white, black = ((0, 0), (448, 448)) if view == "white-bottom" else ((448, 448), (0, 0))
    tag, white_cls, black_cls = (("cg-board", "white rook", "black king") if platform == "lichess"
                                 else ("wc-chess-board", "piece wr", "piece bk"))
    piece_tag = "piece" if platform == "lichess" else "div"
    w_url = "wrong.svg" if fault == "wrong-artwork" else "piece/merida/wR.svg"
    if fault == "wrong-pieces":
        white_cls = "white queen" if platform == "lichess" else "piece wq"
    x = -40 if fault == "clipped" else 64
    overlay = '<square style="position:absolute;inset:0;background:red"></square>' if fault == "marking" else ""
    cover = '<div style="position:fixed;inset:0;background:gray;z-index:99"></div>' if fault == "dialog" else ""
    cls = "orientation-black" if view == "black-bottom" else "orientation-white"
    return f"""<html><head><style>
    {tag} {{display:block;position:absolute;left:{x}px;top:80px;width:512px;height:512px;
       background-image:url('https://fixture.test/images/board/green.png');}}
    {tag} > {piece_tag} {{position:absolute;display:block;width:64px;height:64px;}}
    </style></head><body data-board="green" data-piece-set="merida">
    <div class="main-board"><div class="cg-wrap {cls}"><{tag}>
    <{piece_tag} class="{white_cls}" style="left:{white[0]}px;top:{white[1]}px;background-image:url('https://fixture.test/{w_url}')"></{piece_tag}>
    <{piece_tag} class="{black_cls}" style="left:{black[0]}px;top:{black[1]}px;background-image:url('https://fixture.test/piece/merida/bK.svg')"></{piece_tag}>
    {overlay}</{tag}></div></div>{cover}
    <script>
    const hashed={{'images/board/green.png':true}};
    for(const c of ['w','b']) for(const r of ['P','N','B','R','Q','K']) hashed[`piece/merida/${{c}}${{r}}.svg`]=true;
    window.site={{manifest:{{hashed}},asset:{{url:p=>'https://fixture.test/'+p}}}};
    const board=document.querySelector('{tag}');
    board.state={{isFlipped:{str(view == 'black-bottom').lower()}}};
    board.options={{themeAssets:{{board:{{assets:{{background:'https://fixture.test/images/board/green.png'}}}},
      pieces:{{assets:{{wr:'https://fixture.test/piece/merida/wR.svg',bk:'https://fixture.test/piece/merida/bK.svg'}}}}}}}};
    board.game={{getOptions:()=>board.options}};
    </script></body></html>"""


def setup(page, content):
    def route(request):
        if request.request.url.startswith("https://fixture.test/"):
            request.fulfill(content_type="image/svg+xml", body='<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64" fill="tan"/></svg>')
        else:
            request.fulfill(content_type="text/html", body=content)
    page.route("**/*", route)


@pytest.mark.integration
@pytest.mark.parametrize("view", ["white-bottom", "black-bottom"])
@pytest.mark.parametrize("factor", [1, 2])
@pytest.mark.parametrize("platform", ["lichess", "chesscom"])
def test_real_png_matches_dom_bounds_orientation_and_requested_scale(browser, monkeypatch, view, factor, platform):
    config = dict(CONFIG, deviceScaleFactor=factor, platform=platform)
    context = browser.new_context(viewport=config["viewport"], device_scale_factor=factor)
    page = context.new_page()
    setup(page, html(view, platform))
    # Offline Chess.com fixture starts configured; live pilot exercises its real selectors.
    monkeypatch.setattr(sites, "select_chesscom", lambda p, b, c: (b.evaluate("e=>e.options.themeAssets"), {}))
    try:
        png, annotation = sites.capture_page(page, PLACEMENT, config, view)
        assert annotation["boardBounds"] == {"x": 64*factor, "y": 80*factor,
                                             "width": 512*factor, "height": 512*factor}
        assert check_png(png, annotation["boardBounds"]) == {"width": 1024*factor, "height": 900*factor}
        assert annotation["source"]["boardArtwork"] == ["https://fixture.test/images/board/green.png"]
    finally:
        context.close()


@pytest.mark.integration
@pytest.mark.parametrize("fault", ["wrong-artwork", "wrong-pieces", "marking", "clipped", "dialog", "changed-during-capture"])
def test_mislabeled_or_obscured_images_are_not_returned(browser, monkeypatch, fault):
    context = browser.new_context(viewport=CONFIG["viewport"])
    page = context.new_page()
    setup(page, html("white-bottom", fault=fault))
    if fault == "changed-during-capture":
        original = page.screenshot
        def change(**kwargs):
            page.locator('piece.white').evaluate("e=>e.className='white queen'")
            return original(**kwargs)
        monkeypatch.setattr(page, "screenshot", change)
    try:
        with pytest.raises(Exception, match="artwork|position|markings|covered|outside"):
            sites.capture_page(page, PLACEMENT, CONFIG, "white-bottom")
    finally:
        context.close()


@pytest.mark.unit
def test_selected_name_is_not_enough_when_actual_artwork_is_wrong():
    snapshot = {"rows": ["R.......", *["........"]*6, ".......k"], "orientation": "white-bottom",
                "style": {"board": "green", "pieces": "merida", "is3d": False},
                "boardArtwork": ["expected-board"], "pieces": [{"code": "wr", "artwork": ["wrong-piece"]}]}
    with pytest.raises(ValueError, match="Actual piece artwork"):
        sites.verify_snapshot(snapshot, PLACEMENT, CONFIG, "white-bottom", {"board": "expected-board", "pieces": {"wr": "expected-piece"}})
    changed = deepcopy(snapshot)
    changed["style"]["board"] = "brown"
    with pytest.raises(ValueError, match="style differs"):
        sites.verify_snapshot(changed, PLACEMENT, CONFIG, "white-bottom")


@pytest.mark.integration
@pytest.mark.parametrize("platform", ["lichess", "chesscom"])
@pytest.mark.parametrize("fault", [None, "position-ignored", "artwork-changed"])
def test_reused_page_checks_new_position_and_view_without_navigation(browser, monkeypatch, platform, fault):
    config = dict(CONFIG, platform=platform)
    context = browser.new_context(viewport=config["viewport"])
    page = context.new_page()
    setup(page, html("white-bottom", platform))
    monkeypatch.setattr(sites, "select_chesscom", lambda p, b, c: (b.evaluate("e=>e.options.themeAssets"), {}))
    try:
        session = sites.CaptureSession(page, config)
        session.capture(PLACEMENT, "white-bottom")
        # A small native-renderer fixture makes updates observable in real DOM
        # geometry. The production checks still inspect the resulting screenshot.
        page.evaluate("""([platform, fault]) => {
          const board=document.querySelector(platform==='lichess'?'cg-board':'wc-chess-board');
          let current='R7/8/8/8/8/8/8/7k', flipped=false;
          function render() {
            const pieces=[...board.children];
            for(const [row,rank] of current.split('/').entries()) {
              let col=0;
              for(const char of rank) {
                if (/\\d/.test(char)) { col+=Number(char); continue; }
                const piece=pieces[char==='R'?0:1];
                piece.style.left=(flipped?7-col:col)*64+'px';
                piece.style.top=(flipped?7-row:row)*64+'px';
                col++;
              }
            }
            board.state.isFlipped=flipped;
            board.closest('.cg-wrap').className='cg-wrap orientation-'+(flipped?'black':'white');
            if(fault==='artwork-changed') pieces[0].style.backgroundImage="url('https://fixture.test/wrong.svg')";
          }
          const flip=document.createElement('button');
          flip.textContent='Flip board'; flip.setAttribute('aria-label','Flip Board');
          flip.onclick=()=>{flipped=!flipped;render();};document.body.append(flip);
          const input=document.createElement('input');input.className='copy-me__target';
          input.onchange=()=>{if(fault!=='position-ignored')current=input.value;render();};
          document.body.append(input);
          board.game.load=({fen})=>{if(fault!=='position-ignored')current=fen;render();};
          board.game.clearMarkings=()=>{};board.game.isAnimating=()=>false;
        }""", [platform, fault])
        navigations = []
        page.on("request", lambda request: navigations.append(request.url) if request.is_navigation_request() else None)
        moved = "1R6/8/8/8/8/8/8/6k1"
        if fault:
            with pytest.raises(ValueError, match="position|artwork"):
                session.capture(moved, "black-bottom")
        else:
            _, annotation = session.capture(moved, "black-bottom")
            assert annotation["source"]["renderedRows"] == [".k......", *["........"]*6, "......R."]
            assert annotation["source"]["renderedOrientation"] == "black-bottom"
            assert "page reused" in annotation["source"]["positionUpdate"]
        assert navigations == []
    finally:
        context.close()


def catalogue():
    """Small invented catalogue: no remote calls or redistributed theme assets."""
    return {
        "boardStyles": [{"isUnlocked": True, "boardStyle": {
            "id": "board-id", "name": "Blue", "supportedPlatforms": ["PLATFORM_WEB"],
            "image": "https://fixture.test/blue.png", "highlightColor": "#ffff00",
            "coordinateColorLight": "#eeeeee", "coordinateColorDark": "#111111"}}],
        "pieceSets": [{"isUnlocked": True, "pieceSet": {
            "id": "pieces-id", "name": "Classic", "supportedPlatforms": ["PLATFORM_WEB"],
            "perspective": "PIECE_PERSPECTIVE_TOP_DOWN",
            "images": {color + role: f"https://fixture.test/{color}-{role}.png"
                       for color in ("white", "black")
                       for role in ("Pawn", "Knight", "Bishop", "Rook", "Queen", "King")}}}],
    }


@pytest.mark.unit
def test_chesscom_catalogue_resolves_all_twelve_roles():
    assets, choices = sites.chesscom_assets(catalogue(), {"boardTheme": "blue", "pieceSet": "classic"})
    assert assets["board"]["assets"]["background"] == "https://fixture.test/blue.png"
    assert len(assets["pieces"]["assets"]) == 12
    assert assets["pieces"]["assets"]["bn"] == "https://fixture.test/black-Knight.png"
    assert assets["pieces"]["assets"]["wk"] == "https://fixture.test/white-King.png"
    assert choices["pieceSet"]["name"] == "Classic"


@pytest.mark.unit
@pytest.mark.parametrize("fault", ["locked", "missing-style", "duplicate", "3d", "mobile-only", "missing-art"])
def test_chesscom_catalogue_rejects_unavailable_or_incomplete_styles(fault):
    data = catalogue()
    if fault == "locked":
        data["pieceSets"][0]["isUnlocked"] = False
    elif fault == "missing-style":
        data["boardStyles"] = []
    elif fault == "duplicate":
        data["boardStyles"] *= 2
    elif fault == "3d":
        data["pieceSets"][0]["pieceSet"]["perspective"] = "PIECE_PERSPECTIVE_3D"
    elif fault == "mobile-only":
        data["boardStyles"][0]["boardStyle"]["supportedPlatforms"] = ["PLATFORM_IOS"]
    else:
        data["pieceSets"][0]["pieceSet"]["images"]["whiteKing"] = ""
    with pytest.raises(ValueError):
        sites.chesscom_assets(data, {"boardTheme": "blue", "pieceSet": "classic"})


@pytest.mark.integration
def test_chesscom_selection_reads_catalogue_and_changes_only_local_renderer(browser):
    context = browser.new_context()
    page = context.new_page()
    endpoint = "https://api.chess.com/rpc/chesscom.themes.v2.ThemesService/ListThemesSelection"
    requests = []
    def serve(route):
        requests.append(route.request.url)
        route.fulfill(json=catalogue(), headers={"access-control-allow-origin": "*"})
    page.route(endpoint, serve)
    page.set_content("""
      <button aria-label="Settings">Settings</button>
      <button id="board-tab">Board</button>
      <button aria-label="Close">Close</button>
      <wc-chess-board></wc-chess-board>
    """)
    page.evaluate("""endpoint => {
      document.querySelector('#board-tab').onclick=()=>fetch(endpoint);
      const board=document.querySelector('wc-chess-board');
      let options={themeAssets:{sound:{assets:{}}}};
      board.game={getOptions:()=>options,setOptions:next=>{options={...options,...next};}};
    }""", endpoint)
    try:
        board = page.locator("wc-chess-board")
        expected, choices = sites.select_chesscom(page, board, {"boardTheme": "blue", "pieceSet": "classic"})
        assert requests == [endpoint]
        assert choices["method"] == "local-board-options"
        assert expected["pieces"]["assets"]["wk"] == "https://fixture.test/white-King.png"
        assert board.evaluate("e=>e.game.getOptions().themeAssets") == expected
    finally:
        context.close()

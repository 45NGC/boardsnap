"""Comparisons must retain image identity and exclude reserved evaluation."""

import pytest

from tools.compare_photo_recovery import matched


def sample(image_id='photo-1', **changes):
    return dict(id=image_id, imageSha256='image-hash', groupId='source-1',
                split='validation') | changes


def test_report_order_does_not_change_pairing():
    before = [sample('a'), sample('b')]
    after = list(reversed(before))
    assert matched(before, after) == [(before[1], after[0]), (before[0], after[1])]


@pytest.mark.parametrize('change', [dict(imageSha256='changed'), dict(groupId='other'),
                                   dict(split='training')])
def test_reject_changed_identity_or_partition(change):
    with pytest.raises(ValueError, match='identity or partition'):
        matched([sample()], [sample(**change)])


@pytest.mark.parametrize('after', [[], [sample(), sample()], [sample('other')]])
def test_reject_missing_duplicate_or_different_images(after):
    with pytest.raises(ValueError, match='same unique images'):
        matched([sample()], after)


def test_reject_final_evaluation_even_when_reports_match():
    rows = [sample(split='evaluation')]
    with pytest.raises(ValueError, match='Reserved evaluation'):
        matched(rows, rows)

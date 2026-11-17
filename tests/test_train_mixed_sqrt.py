"""The weight ablation may change only the training-derived class weights."""
from copy import deepcopy
import json

import numpy as np
import pytest
import torch

from tools.train_mixed_sqrt import check_weight_plan, sqrt_class_weights
from tools.prepare_phone_photos import ROOT


def plans():
    old = json.loads((ROOT / 'data/manifests/neural-mixed-empty-guard-v1-plan.json').read_text())
    new = deepcopy(old)
    new['runDirectory'] = '.cache/test-sqrt'
    new['loss']['classWeights'] = sqrt_class_weights(old['loss']['classCounts'])
    return new, old


def test_less_extreme_weights_from_training_counts_only():
    new, old = plans()
    check_weight_plan(new, old)
    a, b = np.array(old['loss']['classWeights']), np.array(new['loss']['classWeights'])
    assert b[11] / b[0] == pytest.approx(np.sqrt(a[11] / a[0]))
    assert b[11] / b[0] == pytest.approx(6.9658, abs=.001)
    assert np.argsort(a).tolist() == np.argsort(b).tolist()


@pytest.mark.parametrize('change', ['acceptance', 'learning-rate', 'teacher-mask', 'counts', 'initial-model'])
def test_other_scientific_changes_rejected(change):
    new, old = plans()
    if change == 'acceptance': new['acceptance']['minimumPhotoExactGain'] = 0
    if change == 'learning-rate': new['trainingConfig']['learningRate'] *= 2
    if change == 'teacher-mask': new['intervention']['excludedExposures'] = 0
    if change == 'counts': new['loss']['classCounts'][0] += 1
    if change == 'initial-model': new['baseline']['path'] = 'another.pt'
    with pytest.raises(ValueError): check_weight_plan(new, old)


def test_arbitrary_weights_and_overwriting_control_rejected():
    new, old = plans()
    new['loss']['classWeights'][0] *= 2
    with pytest.raises(ValueError): check_weight_plan(new, old)
    new, old = plans()
    new['runDirectory'] = old['runDirectory']
    with pytest.raises(ValueError): check_weight_plan(new, old)


def test_missing_classes_rejected():
    with pytest.raises(ValueError): sqrt_class_weights([0] + [1] * 12)


def test_weighted_mean_loss_is_invariant_to_global_weight_scale():
    # We need no extra normalization hyperparameter: PyTorch divides by selected weights.
    weights = torch.tensor(sqrt_class_weights([1000] + [10] * 12))
    logits = torch.arange(39, dtype=torch.float32).reshape(3, 13) / 10
    labels = torch.tensor([0, 7, 11])
    a = torch.nn.functional.cross_entropy(logits, labels, weight=weights)
    b = torch.nn.functional.cross_entropy(logits, labels, weight=weights * 10)
    assert a.item() == pytest.approx(b.item())

from datetime import timedelta
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock
from django.utils import timezone

from apps.crm.intelligence import score_customer



class LeadScoringRuleTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.customer = SimpleNamespace(requirements=MagicMock())
        self.customer.requirements.all.return_value = []

    def test_base_score_and_low_readiness(self):
        score, level, factors = score_customer(self.customer, [], [], [], self.now)
        self.assertEqual(score, 20)
        self.assertEqual(level, "LOW")
        self.assertTrue(factors)

    def test_recent_interaction_and_requirement_raise_score(self):
        self.customer.requirements.all.return_value = [SimpleNamespace(is_active=True)]
        interaction = SimpleNamespace(created_at=self.now - timedelta(days=2))
        score, level, _ = score_customer(self.customer, [interaction], [], [], self.now)
        self.assertGreaterEqual(score, 50)
        self.assertLessEqual(score, 60)
        self.assertEqual(level, "MEDIUM")

    def test_overdue_task_penalty_and_active_negotiation_bonus(self):
        task = SimpleNamespace(due_at=self.now - timedelta(days=1))
        negotiation = SimpleNamespace(status="BARGAINING")
        score, level, factors = score_customer(self.customer, [], [task], [negotiation], self.now)
        self.assertEqual(score, 40)
        self.assertEqual(level, "MEDIUM")
        self.assertTrue(any(f["delta"] < 0 for f in factors))

    def test_score_is_clamped(self):
        interactions = [SimpleNamespace(created_at=self.now) for _ in range(100)]
        negotiations = [SimpleNamespace(status="PRE_AGREEMENT") for _ in range(10)]
        score, _, _ = score_customer(self.customer, interactions, [], negotiations, self.now)
        self.assertEqual(score, 100)

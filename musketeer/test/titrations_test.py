"""
Test case and suite for Titration

@author: mark
"""

import unittest
import logging
import musketeer.titration as titration

logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.WARN)


class TitrationTestCase(unittest.TestCase):
    """Example Test case for Titration."""

    def setUp(self):
        """Test set up."""
        self.t = titration.Titration()

    def tearDown(self):
        """Clean up after tests."""
        del self.t

    def test_totalCount(self):
        """Example test."""
        result = self.t.totalCount
        
        self.assertEqual(1, result)

    def test_freeCount(self):
        """Example test."""
        result = self.t.freeCount

        self.assertEqual(0, result)


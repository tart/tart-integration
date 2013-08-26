#!/usr/bin/env python3

from libtart.checker import PagerDutyJira

checker = PagerDutyJira()
checker.checkPagerDuty()
checker.checkJira()


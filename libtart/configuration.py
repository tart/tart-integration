#!/usr/bin/env python
# -*- coding: utf-8 -*-
##
# Tart Integration
#
# Copyright (c) 2013, Tart İnternet Teknolojileri Ticaret AŞ
#
# Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby
# granted, provided that the above copyright notice and this permission notice appear in all copies.
#
# The software is provided "as is" and the author disclaims all warranties with regard to the software including all
# implied warranties of merchantability and fitness. In no event shall the author be liable for any special, direct,
# indirect, or consequential damages or any damages whatsoever resulting from loss of use, data or profits, whether
# in an action of contract, negligence or other tortious action, arising out of or in connection with the use or
# performance of this software.
##

import configparser

class ConfigParser(configparser.SafeConfigParser):
    def __init__(self, filename, *attributes, **paramters):
        configparser.SafeConfigParser.__init__(self, *attributes, **paramters)
        self.read(filename)

    def check(self, section, option):
        if self.has_option(section, option):
            return self.getboolean(section, option)

    def filter(self, section, option, item):
        if self.has_option(section, option):
            return item in (value.strip() for value in self.get(section, option).split(','))


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

import signal
import fcntl

class Timeout (Exception): pass

class SingleUserDatabase:
    '''Database to read and write only one value; block everything when used.'''
    __enterTimeoutSeconds = 10
    __openTimeoutSeconds = 300

    def __timeoutRaiser(self, *arguments):
        raise Timeout

    def __init__(self, filename):
        self.__filename = filename
        signal.signal(signal.SIGALRM, self.__timeoutRaiser)

    def __enter__(self):
        self.__pointer = open(self.__filename, 'a+')
        signal.alarm(self.__enterTimeoutSeconds)
        fcntl.lockf(self.__pointer, fcntl.LOCK_EX) 
        signal.alarm(self.__openTimeoutSeconds)
        return self

    def read(self):
        self.__pointer.seek(0)
        return self.__pointer.read().strip()

    def write(self, value):
        self.__pointer.seek(0)
        self.__pointer.truncate()
        return self.__pointer.write(value)

    def __exit__(self, *arguments):
        self.__pointer.close()
        signal.alarm(0)


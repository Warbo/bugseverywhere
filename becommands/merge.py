# Copyright (C) 2005 Aaron Bentley and Panometrics, Inc.
# <abentley@panoramicfeedback.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""Merge duplicate bugs"""
from libbe import cmdutil, bugdir
import os, copy
__desc__ = __doc__

def execute(args):
    """
    >>> from libbe import utility
    >>> bd = bugdir.simple_bug_dir()
    >>> a = bd.bug_from_shortname("a")
    >>> a.comment_root.time = 0
    >>> dummy = a.new_comment("Testing")
    >>> dummy.time = 1
    >>> dummy = dummy.new_reply("Testing...")
    >>> dummy.time = 2
    >>> b = bd.bug_from_shortname("b")
    >>> b.status = "open"
    >>> b.comment_root.time = 0
    >>> dummy = b.new_comment("1 2")
    >>> dummy.time = 1
    >>> dummy = dummy.new_reply("1 2 3 4")
    >>> dummy.time = 2
    >>> bd.save()
    >>> os.chdir(bd.root)
    >>> execute(["a", "b"])
    Merging bugs a and b
    >>> bd._clear_bugs()
    >>> a = bd.bug_from_shortname("a")
    >>> a.load_comments()
    >>> mergeA = a.comment_from_shortname(":3")
    >>> mergeA.time = 3
    >>> print a.string(show_comments=True)
              ID : a
      Short name : a
        Severity : minor
          Status : open
        Assigned : 
          Target : 
         Creator : John Doe <jdoe@example.com>
         Created : Wed, 31 Dec 1969 19:00 (Thu, 01 Jan 1970 00:00:00 +0000)
    Bug A
    --------- Comment ---------
    Name: a:1
    From: wking <wking@thor.yang.physics.drexel.edu>
    Date: Thu, 01 Jan 1970 00:00:01 +0000
    <BLANKLINE>
    Testing
    --------- Comment ---------
    Name: a:2
    From: wking <wking@thor.yang.physics.drexel.edu>
    Date: Thu, 01 Jan 1970 00:00:02 +0000
    <BLANKLINE>
    Testing...
    --------- Comment ---------
    Name: a:3
    From: wking <wking@thor.yang.physics.drexel.edu>
    Date: Thu, 01 Jan 1970 00:00:03 +0000
    <BLANKLINE>
    Merged from bug b
    --------- Comment ---------
    Name: a:4
    From: wking <wking@thor.yang.physics.drexel.edu>
    Date: Thu, 01 Jan 1970 00:00:01 +0000
    <BLANKLINE>
    1 2
    --------- Comment ---------
    Name: a:5
    From: wking <wking@thor.yang.physics.drexel.edu>
    Date: Thu, 01 Jan 1970 00:00:02 +0000
    <BLANKLINE>
    1 2 3 4
    >>> b = bd.bug_from_shortname("b")
    >>> b.load_comments()
    >>> mergeB = b.comment_from_shortname(":3")
    >>> mergeB.time = 3
    >>> print b.string(show_comments=True)
              ID : b
      Short name : b
        Severity : minor
          Status : closed
        Assigned : 
          Target : 
         Creator : Jane Doe <jdoe@example.com>
         Created : Wed, 31 Dec 1969 19:00 (Thu, 01 Jan 1970 00:00:00 +0000)
    Bug B
    --------- Comment ---------
    Name: b:1
    From: wking <wking@thor.yang.physics.drexel.edu>
    Date: Thu, 01 Jan 1970 00:00:01 +0000
    <BLANKLINE>
    1 2
    --------- Comment ---------
    Name: b:2
    From: wking <wking@thor.yang.physics.drexel.edu>
    Date: Thu, 01 Jan 1970 00:00:02 +0000
    <BLANKLINE>
    1 2 3 4
    --------- Comment ---------
    Name: b:3
    From: wking <wking@thor.yang.physics.drexel.edu>
    Date: Thu, 01 Jan 1970 00:00:03 +0000
    <BLANKLINE>
    Merged into bug a
    >>> print b.status
    closed
    """
    options, args = get_parser().parse_args(args)
    if len(args) < 2:
        raise cmdutil.UserError("Please two bug ids.")
    if len(args) > 2:
        help()
        raise cmdutil.UserError("Too many arguments.")
    
    bd = bugdir.BugDir(from_disk=True)
    bugA = bd.bug_from_shortname(args[0])
    bugA.load_comments()
    bugB = bd.bug_from_shortname(args[1])
    bugB.load_comments()
    mergeA = bugA.new_comment("Merged from bug %s" % bugB.uuid)
    newCommTree = copy.deepcopy(bugB.comment_root)
    for comment in newCommTree.traverse():
        comment.bug = bugA
    for comment in newCommTree:
        mergeA.add_reply(comment, allow_time_inversion=True)
    bugB.new_comment("Merged into bug %s" % bugA.uuid)
    bugB.status = "closed"
    bd.save()
    print "Merging bugs %s and %s" % (bugA.uuid, bugB.uuid)

def get_parser():
    parser = cmdutil.CmdOptionParser("be merge BUG-ID BUG-ID")
    return parser

longhelp="""
The second bug (B) is merged into the first (A).  This adds merge
comments to both bugs, closes B, and appends B's comment tree to A's
merge comment.
"""

def help():
    return get_parser().help_str() + longhelp
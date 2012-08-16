import sys

import shaper

def from_rules(rule_string):
    return ProgressiveRuleMatcher(rule_string)

class RuleMatch(object):
    def __init__(self, start_byte, end_byte, action):
        self._start_byte = int(start_byte)
        self._end_byte = int(end_byte)
        self._action = action

    def start_byte(self):
        return self._start_byte

    def end_byte(self):
        return self._end_byte

    def action(self):
        return self._action

    def __str__(self):
        return "RuleMatch(start_byte=%s, end_byte=%s, action=%s)" % (self._start_byte, self._end_byte, self._action)

    def __repr__(self):
        return self.__str__()

    def __cmp__(self, other):
        if isinstance(other, self.__class__):
            return cmp(self._start_byte, other.start_byte())
        return -1

class ProgressiveRuleMatcher(object):

    def __init__(self, rule_string):
        """Build a Matcher from the rulestring. PErforms the parsing and validation"""
        # parse the rules
        if not rule_string:
            raise ValueError("Rule string cannot be empty or None")

        self._rule_matches = list()
        
        # split rule definitions by ','
        rules = rule_string.split(",")
        
        for rule in rules:
            # split the match from the action by '~'
            match, action = rule.split("~")
            self._validate_match(match)
            self._validate_action(action)

            start_byte, end_byte = match[1:].split("-")
            
            if end_byte == '*':
                end_byte = sys.maxint

            self._rule_matches.append(RuleMatch(start_byte, end_byte, action))

        self._rule_matches.sort()

        self._check_for_overlaps_in_matches()

    def get_action(self, start_byte, end_byte):
        """Given a byte range, determine if there is an action that should be performed"""

        # This is an O(n) search which is not as efficient as it could be, but given that the value of N 
        # will be very low < 3 (typically) this should be sufficient
        start_byte = int(start_byte)
        end_byte = int(end_byte)

        matches = []

        for match in self._rule_matches:
            if (start_byte >= match.start_byte() and start_byte <= match.end_byte()) or \
               (end_byte >= match.start_byte() and end_byte <= match.end_byte()) or \
               (start_byte <= match.start_byte() and end_byte >= match.end_byte()):

                matches.append(match)
        
        if len(matches) == 1:
            return matches[0].action()
        elif len(matches) == 0:
            return None
        else:
            largest_intersection = 0
            best_match = None
            for match in matches:
                start_index = max(start_byte, match.start_byte())
                end_index = min(end_byte, match.end_byte())
                intersection = end_index - start_index
                if largest_intersection < intersection:
                    best_match = match
                    largest_intersection = intersection
            return best_match.action()


    # Private methods

    def _validate_match(self, match):
        if not match:
            raise ValueError("No match specified")
        if match[0] != 'b':
            raise ValueError("Invalid match '%s'. Only supported match is byte range queries: 'bxxx-yyy'" % match)

    def _validate_action(self, action):
        shaper.validate_action_part(action)

    def _check_for_overlaps_in_matches(self):
        last_match = None
        for rule_match in self._rule_matches:
            if last_match is not None and rule_match.start_byte() <= last_match.end_byte():
                raise ValueError("Rules '%s' and '%s' overlap in their byte ranges" % (last_match, rule_match))
            last_match = rule_match
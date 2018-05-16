from pecan.hooks import PecanHook

import traceback


#
# error hook
#
class ErrorHook(PecanHook):

    def on_error(self, state, exc):
        traceback.print_exception(exc)

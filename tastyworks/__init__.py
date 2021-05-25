import logging
import sys

# create logger
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.propagate = False

# create file handler which logs even debug messages
fh = logging.StreamHandler(sys.stdout)
fh.setLevel(logging.DEBUG)

# create formatter and add it to the handlers
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
formatter = logging.Formatter('%(asctime)s - %(message)s')

fh.setFormatter(formatter)

# add the handlers to the logger
log.addHandler(fh)


root = logging.getLogger()
root.addHandler(fh)
root.propagate = False
root.setLevel(logging.DEBUG)

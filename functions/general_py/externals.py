# Add external libraries:
import os
import sys


# If this line confuses you, then I feel bad. Sorry.
# https://stackoverflow.com/questions/5137497/find-current-directory-and-files-directory
# Also note the comment below the correct answer:
#
# "I hate it when I use this to append to sys.path. I feel so dirty right now."
#
FUNCTION_PATH = os.path.abspath(
    os.path.normpath(os.path.dirname(os.path.realpath(__file__)) + "/../")
)

sys.path.append(FUNCTION_PATH + "/external_py/coloredlogs")
sys.path.append(FUNCTION_PATH + "/external_py/f90nml")
sys.path.append(FUNCTION_PATH + "/external_py/humanfriendly")
sys.path.append(FUNCTION_PATH + "/external_py/importlib")
sys.path.append(FUNCTION_PATH + "/external_py/six")
sys.path.append(FUNCTION_PATH + "/external_py/tqdm")
# Always keep this one last:
sys.path.append(FUNCTION_PATH + "/external_py/")

# The YAML Lib isn't python agnostic
import six

if six.PY2:
    sys.path.append(FUNCTION_PATH + "/external_py/pyyaml/lib")
    sys.path.append(FUNCTION_PATH + "/external_py/pyyaml/lib/yaml")
    # Mock isn't available in py2
    sys.path.append(FUNCTION_PATH + "/external_py/mock/")

elif six.PY3:
    sys.path.append(FUNCTION_PATH + "/external_py/pyyaml/lib3")
    sys.path.append(FUNCTION_PATH + "/external_py/pyyaml/lib3/yaml")
    

if os.environ.get("RUNNING_CI") == "1":
    six.print_(sys.path)

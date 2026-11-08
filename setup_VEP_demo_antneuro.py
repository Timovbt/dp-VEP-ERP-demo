from pathlib import Path
import shutil
import subprocess
import sys

# ----------------------------------------------------------------------------
# Install requirements
# ----------------------------------------------------------------------------

requirements = ["GitPython", "toml"]

for req in requirements:
    try:
        __import__(req)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", req])

from git import Repo
import toml

# ----------------------------------------------------------------------------
# Set up
# ----------------------------------------------------------------------------

# The name of the folder that is to be created to store all the modules
SETUP_FOLDER_NAME = "VEP-demo-env"
BRANCH_NAME = SETUP_FOLDER_NAME  # used within each module

CONTROL_ROOM_URL = "https://github.com/bsdlab/dp-control-room.git"
DECODER_URL = "https://github.com/Timovbt/dp-visualisation.git"
STIMULATION_URL = "https://github.com/Timovbt/dp-stimulation-demo.git"
MOCKUP_URL = "https://github.com/bsdlab/dp-mockup-streamer.git"

DATA_STREAM_NAME = 'EE225-000000-000945-02-DCC-TMSI-02'
MARKER_STREAM_NAME = "stimulation-marker-stream"
DECODER_STREAM_NAME = "output-average-stream"

# ----------------------------------------------------------------------------
# Grab the git repositories
# ----------------------------------------------------------------------------

root_dir = Path(SETUP_FOLDER_NAME)
try:
    root_dir.mkdir(exist_ok=False)
except FileExistsError:
    print(f"Directory `{root_dir}` already exists. Exiting.")
    q = input("Do you want to overwrite it? [y/N] ")
    if q == "y":
        shutil.rmtree(root_dir)
        root_dir.mkdir()
    else:
        exit(1)

# SSH ide via the Repo.clone_from did not work -> use manual subprocess calls
repos = []
repo_dirs = ["dp-control-room", "dp-visualisation", "dp-stimulation-demo",'dp-mockup-streamer']
for url, repo_dir in zip([CONTROL_ROOM_URL, DECODER_URL, STIMULATION_URL, MOCKUP_URL], repo_dirs):
    cmd = f'git clone -v -- {url} {SETUP_FOLDER_NAME}/{repo_dir}'
    subprocess.run(cmd, shell=True)
    repos.append(Repo(root_dir / repo_dir))

# for each repo -> create a branch for the experiment
# Keep a branch for the local setup to separate local specific changes
# from general bugfixes and features (which would then be merged back to `main`)
for repo in repos:
    branch = repo.create_head(BRANCH_NAME)
    branch.checkout()

# ----------------------------------------------------------------------------
# Derived paths
# ----------------------------------------------------------------------------

# Data directory relative to SETUP_FOLDER_NAME
DATA_DIR = root_dir.joinpath("./data").resolve()

# ----------------------------------------------------------------------------
# Create configs
# ----------------------------------------------------------------------------

#
# >>> for dp-control-room
#

control_room_cfg = f"""

[python]
modules_root = '../'                                                            

# -------------------- Stimulation  ----------------------------------------- 
[python.modules.dp-stimulation-demo]                                     
    type = 'stimulation'
    port = 8084
    ip = '127.0.0.1'
    retry_connection_after_s = 3  

# -------------------- Visualisation  ---------------------------------------
[python.modules.dp-visualisation]                                        
    type = 'visualisation'
    port = 8085
    ip = '127.0.0.1'
    retry_connection_after_s = 2

# -------------------- Mockup-streamer (for test purposes)  ---------------------------------------
[python.modules.dp-mockup-streamer]                                        
    type = 'EEG'
    port = 8086
    ip = '127.0.0.1'


# -------------------- LSL recording -----------------------------------------
#[python.modules.dp-lsl-recording]                                      
#    type = 'recording'
#    port = 8082                                                                 
#    ip = '127.0.0.1'


# [macros]



# [macros.stop_streaming]
#     name = 'STOP LSL RECORDING'
#     description = 'Stop the recording'
# [macros.stop_streaming.cmds]
#     com1 = ['dp-lsl-recording', 'STOPRECORD']

# [macros.run_online]
#     name = 'RUN ONLINE'
#     description = 'Start the recording of online data'
# [macros.run_online.default_json]
#     fname = 'sub-P001_ses-S001_run-001_task-online'
#     data_root = '{str(DATA_DIR.resolve())}' 
#[macros.run_online.cmds]
#     # [<target_module>, <PCOMM>, <kwarg_name1 (optional)>, <kwarg_name2 (optional)>]
#    com1 = ['dp-lsl-recording', 'UPDATE']
#    com2 = ['dp-lsl-recording', 'SELECT_ALL']
#    com3 = ['dp-lsl-recording', 'SET_SAVE_PATH', 'fname=fname', 'data_root=data_root']
#    com4 = ['dp-lsl-recording', 'RECORD']
#    com5 = ['dp-cvep-decoder', 'DECODE ONLINE']
"""

control_room_cfg_pth = Path("./" + SETUP_FOLDER_NAME + "/dp-control-room/configs/cvep_speller.toml")
with open(control_room_cfg_pth, "w") as f:
    f.write(control_room_cfg)


#dp-visualisation

decoder_cfg_pth = root_dir.joinpath("dp-visualisation/configs/config.toml")
cfg = toml.load(decoder_cfg_pth)

cfg["data"]["data_root"] = str(DATA_DIR.resolve())
cfg["data"]["selected_channels"] = [1,25,28,29,30,63]
cfg['data']['selected_channel_names'] = ['Fz','O1','Pz','POz','Oz','O2']
cfg["data"]["capfile"] = str(root_dir.joinpath("dp-cvep-decoder/cvep_decoder/caps/biosemi6.loc").resolve())


cfg["streams"]["marker_stream_name"] = MARKER_STREAM_NAME
cfg["streams"]["data_stream_name"] = DATA_STREAM_NAME
cfg["streams"]["decoder_stream_name"] = DECODER_STREAM_NAME

cfg["visualisation"]["output_port"] = 8088
cfg["visualisation"]["output_address"] = '127.0.0.1'

toml.dump(cfg, open(decoder_cfg_pth, "w"))


#dp-stimulation

stimulation_cfg_pth = root_dir.joinpath("dp-stimulation-demo/configs/stimulation.toml")
cfg = toml.load(stimulation_cfg_pth)

cfg["streams"]["marker_stream_name"] = MARKER_STREAM_NAME
cfg["stimulation"]["screen"]["resolution"] = [1920, 1080]

cfg['stimulation']['stimuli']['size'] = [500,500] #size in px
cfg['stimulation']['stimuli']['fixation_cross_size']

cfg["stimulation"]["timing"]["n_flashes"] = 500
cfg["stimulation"]["timing"]["flash_duration"] = 30
cfg["stimulation"]["timing"]["random_interval"] = [500,750]

toml.dump(cfg, open(stimulation_cfg_pth, "w"))


#mockup
mockup_cfg_pth = root_dir.joinpath("dp-mockup-streamer/config/streams.toml")
cfg = toml.load(mockup_cfg_pth)

cfg['random']['stream1']['stream_name'] = DATA_STREAM_NAME
cfg['random']['stream1']['n_channels'] = 64
toml.dump(cfg, open(mockup_cfg_pth, "w"))
# ----------------------------------------------------------------------------
# Create single run script in the control room
# ----------------------------------------------------------------------------

platform = sys.platform
suffix = ".ps1" if platform == "win32" else ".sh"

script_file = root_dir.resolve() / "dp-control-room" / f"run_VEP_demo{suffix}"
script_plot_file = root_dir.resolve() / "dp-control-room" / f"run_plot{suffix}"
with open(script_file, "w") as f:
    f.write(f'python -m control_room.main --setup_cfg_path="{control_room_cfg_pth.resolve()}"')
with open(script_plot_file, "w") as f:
    f.write(f'cd "{root_dir.resolve() / "dp-visualisation"}" \n')
    f.write("python -m visualisation.live_plot")

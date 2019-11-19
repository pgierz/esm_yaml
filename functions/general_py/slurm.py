import sys, os

class slurm:
    def __init__(self, config):
        folder = config["general"]["thisrun_scripts_dir"]
        self.filename = "hostfile_srun"
        self.path = folder + "/" + self.filename

    def check_if_submitted(self):
        jobid = os.environ.get('SLURM_JOB_ID', None)
        if jobid:
            return True
        else:
            return False

    def get_jobid(self):
        jobid = os.environ.get('SLURM_JOB_ID', None)
        if jobid:
            return jobid
        else:
            return None

    def calc_requirements(self, config):
        start_proc = 0
        end_proc = 0
        with open(self.path, "w") as hostfile:
            for model in config["general"]["models"]:
                if "nproc" in config[model]:
                    end_proc = start_proc + int(config[model]["nproc"]) - 1
                elif "nproca" in config[model] and "nprocb" in config[model]:    
                    end_proc = start_proc + int(config[model]["nproca"])*int(config[model]["nprocb"]) - 1
                else:
                    continue
                if "execution_command" in config[model]:
                    command = "./" + config[model]["execution_command"]
                elif "executable" in config[model]:
                    command = "./" + config[model]["executable"]
                else: 
                    continue
                hostfile.write(str(start_proc) + "-" + str(end_proc) + "  " + command + "\n")
                start_proc = end_proc + 1

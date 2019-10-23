import sys
known_batch_systems = ["slurm"]

class esm_batch_system:
    def __init__(self, config, name):
        self.name = name
        if name == "slurm":
            import slurm
            self.bs = slurm.slurm(config)
        else:
            print ("Unknown batch system: ", name)
            sys.exit(1)



import sys
known_couplers = ["oasis3mct"]

class esm_coupler:

    def __init__(self, full_config, name):
        self.name = name

        self.process_ordering = full_config[name]["process_ordering"]
        self.coupled_execs = []
        for exe in self.process_ordering:
            self.coupled_execs.append(full_config[exe]["executable"])
        self.runtime=full_config["general"]["runtime"][5]
        self.nb_of_couplings = 0
        if "coupling_target_fields" in full_config[self.name]:
            for restart_file in list(full_config[self.name]["coupling_target_fields"]):
                self.nb_of_couplings += len(list(full_config[self.name]["coupling_target_fields"][restart_file]))
        if name == "oasis3mct":
            import oasis
            self.coupler = oasis.oasis(self.nb_of_couplings,  self.coupled_execs, self.runtime)
        else:
            print ("Unknown coupler :", name)
            sys.exit(0)

    def prepare(self, full_config, destination_dir):
        self.add_couplings(full_config)
        self.finalize(destination_dir)
    
    def add_couplings(self, full_config):
        if "coupling_target_fields" in full_config[self.name]:
            for restart_file in list(full_config[self.name]["coupling_target_fields"]):
                for coupling in full_config[self.name]["coupling_target_fields"][restart_file]:
                        coupling = coupling.replace("<--", "%").replace("--", "&")
                        leftside, rest = coupling.split("%")
                        leftside=leftside.strip()
                        interpolation, rightside = rest.split("&")
                        rightside=rightside.strip()
                        if ":" in leftside:
                            lefts = leftside.split(":")
                        else:
                            lefts = [leftside]
                            
                        if ":" in rightside:
                            rights = rightside.split(":")
                        else:
                            rights = [rightside]

                        if not len(lefts) == len(rights):
                            print ("Left and right side of coupling don't match: ", coupling)
                            sys.exit(0)

                         
                        left_grid = left_nx = left_ny = None
                        right_grid = right_nx = right_ny = None
                        for left, right in zip(lefts, rights):
                            found_left = found_right = False
                            for model in list(full_config):
                                if "coupling_fields" in full_config[model]:
                                    if left in full_config[model]["coupling_fields"]:
                                        found_left = True
                                        if not left_grid:
                                            left_grid = full_config[model]["coupling_fields"][left]["grid"]
                                            left_nx = full_config[model]["grids"][left_grid]["nx"]
                                            left_ny = full_config[model]["grids"][left_grid]["ny"]
                                        else:
                                            if not left_grid == full_config[model]["coupling_fields"][left]["grid"]: 
                                                print ("All fields coupled together need to exist on same grid")
                                                sys.exit(0)
                                    if right in full_config[model]["coupling_fields"]:
                                        found_right =True
                                        if not right_grid:
                                            right_grid = full_config[model]["coupling_fields"][right]["grid"]
                                            right_nx = full_config[model]["grids"][right_grid]["nx"]
                                            right_ny = full_config[model]["grids"][right_grid]["ny"]
                                        else:
                                            if not right_grid == full_config[model]["coupling_fields"][right]["grid"]:
                                                print ("All fields coupled together need to exist on same grid")
                                                sys.exit(0)
                                    if found_right and found_left:
                                        break
                            if not found_left:
                                print("Coupling var not found: ", left)
                            if not found_right:
                                print("Coupling var not found: ", right)
                            if not found_left or not found_right:
                                sys.exit(0)
                            
                        self.coupler.add_coupling(lefts, rights)

    
    def finalize(self, destination_dir):
        self.coupler.finalize(destination_dir)

                        




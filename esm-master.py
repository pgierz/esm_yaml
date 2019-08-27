#import fileinput, os, sys, getopt
import sys

#class general_infos:
#	def __init__(self):
#		self.emc = {}
#
#		if os.path.isfile("~/.esm-master.conf"):
#		    with open("~/.esm-master.conf") as myfile:
#				for line in myfile:
#					name, var = line.partition("=")[::2]
#					self.emc[name.strip()] = var.strip()
#		else:
#			print "No configuration file ~/.esm-master.conf found."
#			sys.exit(1)
#
#		if os.path.isfile(".esm-master.conf"):
#		    with open(".esm-master.conf") as myfile:
#				for line in myfile:
#					name, var = line.partition("=")[::2]
#					self.emc[name.strip()] = var.strip()
#
#                gitlab_username=self.emc["DKRZ_GITLAB_USERNAME"]
#		swrepo_username=self.emc["SWREPO_USERNAME"]
#		self.esm_master_dir=self.emc["ESM_MASTER_DIR"]
#		self.esm_environment_dir=self.emc["ESM_ENVIRONMENT_DIR"]
#		self.esm_runscripts_dir=self.emc["ESM_RUNSCRIPTS_DIR"]



#class model_infos:
#
#		if os.path.isfile("yaml/setups2models.yaml"):
#		    with open("yaml/setups2models.yaml") as myfile:
#
#                            # yaml parser aufruf
#
#
#				for line in myfile:
#					name, var = line.partition("=")[::2]
#					self.s2m[name.strip()] = var.strip()
#
#
#
#
#
#
#
#
#
#
#
#
#class cpl_setup:
#	def __init__(self, inlist, setupname=None, mpi=None):
#
#		self.mi=model_infos()
#	
#		self.combination=0
#		self.liste=[]
#
#		self.mpi=mpi
#
#		for setupkey, setupvalues in self.mi.standard_setups.items():
#			if inlist==setupvalues:
#				setupname=setupkey
#				self.liste=setupvalues
#
#		if setupname==None:
#			for listentry in inlist:
#				if listentry in self.mi.standard_setups:
#					print self.mi.standard_setups[listentry]
#					for newcomp in self.mi.standard_setups[listentry]:
#						self.liste.append(newcomp)
#				else:
#					self.liste.append(listentry)
#
#		for comp in self.liste:
#			if comp in self.mi.number_values:
#				self.combination=self.combination+self.mi.number_values[comp]
#			else:
#				print "Unknown model: "+comp
#				sys.exit(1)
#
#		if not self.combination in self.mi.allowed_standalones + self.mi.allowed_combs + self.mi.allowed_sets:
#			print "This combination is not supported."
#			sys.exit(1) 
#
#		if setupname==None:
#			if len(inlist) == 1:
#				if len(self.liste) == 1:   # standalone		
#					self.name=inlist[0]
#					print "name:",self.name
#					self.targetdir=self.mi.masterdir+"/"+self.name
#					self.name="."
#				else:
#					self.name=inlist[0]
#					self.targetdir=self.mi.masterdir+"/"+self.name
#			else:
#				self.name="setup"+str(self.combination)
#		else:
#			self.targetdir=self.mi.masterdir
#			self.name=setupname
#
#
#	def download(self):
#		if os.path.isdir(self.mi.masterdir+"/"+self.name):
#			print "Model "+self.name+" already installed. Nothing to do."
#		else:
#			print "downloading now"
#			if len(self.liste) == 1:   # standalone		
#				self.targetdir=self.mi.masterdir+"/"+self.liste[0]
#				os.system("mkdir -p "+self.targetdir)
#			else:
#				self.targetdir=self.mi.masterdir+"/"+self.name
#				os.system("mkdir -p "+self.targetdir)
#
#			os.chdir(self.mi.masterdir+"/"+self.name)
#
#			for comp in self.liste:
#				if comp in self.mi.downloads_git:
#					try:
#						syscall="git clone https://"+self.mi.downloads_git[comp]
#						os.system(syscall)
#					except:
#						print "No way found to download "+comp
#						sys.exit(1)
#				elif comp in self.mi.downloads_svn:
#					try:
#						syscall="svn checkout "+self.mi.downloads_svn[comp]+' '+comp
#						os.system(syscall)
#					except:
#						print "No way found to download "+comp
#						sys.exit(1)
#
#			if self.combination in self.mi.apply_changes:
#				for method in self.mi.apply_changes[self.combination]:
#					method() #???
#			os.system("mkdir -p "+self.targetdir+"/bin")
#			os.system("mkdir -p "+self.targetdir+"/lib")
#			os.chdir(self.mi.masterdir)
#
#
#	def make(self, command="compile"):
#		print sorted(self.liste, key=lambda comp: self.mi.number_values[comp], reverse=True)
#		for comp in sorted(self.liste, key=lambda comp: self.mi.number_values[comp], reverse=True):
#			proceed=0
#			if command == "compile":
#				if comp in self.mi.compile_commands:
#					makecommand=self.mi.compile_commands[comp]
#					proceed=1
#			elif command == "clean":
#				if comp in self.mi.clean_commands:
#					makecommand=self.mi.clean_commands[comp]
#					proceed=1
#			elif command == "configure":
#				if comp in self.mi.configure_commands:
#					makecommand=self.mi.configure_commands[comp]
#					proceed=1
#	
#			if proceed == 1:
#				try:
#					toplevel=self.name
#					mpi=self.mpi
#					syscall="./make_temp.ksh "+comp+ " "+toplevel+"/"+comp+" " + makecommand + " " + mpi
#					os.system(syscall)
#				except:
#					print "Something went wrong attempting "+command+" "+comp
#					sys.exit(1)
#
#				if command == "compile":
#					if comp in self.mi.install_bins:
#						print "Something to install..."
#						for target in self.mi.install_bins[comp]:
#							print "..."+target
#							syscall="cp "+toplevel+"/"+comp+"/"+target+" "+self.targetdir+"/bin"
#							os.system(syscall)
#					elif comp in self.mi.install_libs:
#						print "Something to install..."
#						for target in self.mi.install_libs[comp]:
#							print "..."+target
#							syscall="cp "+toplevel+"/"+comp+"/"+target+" "+self.targetdir+"/lib"
#							os.system(syscall)
#
#
#
def main(args):

		print "args:", args
#		opts,args=getopt.getopt(args, 'c:n:m:')
#
#		command="all"
#		setupname=None
#               mpi="intelmpi"

#		for opt,val in opts:
#			if opt == '-c':
#				command=val
#			elif opt == '-n':
#				setupname=val
#			elif opt == '-m':
#				mpi=val
#		setup=cpl_setup(args, setupname, mpi)
#
#		
#		if command == "all":
#			setup.download()
#			setup.make("configure")
#			setup.make("compile")
#		elif command == "download":
#			setup.download()
#		else:
#			setup.make(command)
#		

if __name__ == "__main__":
	main(sys.argv[1:])
	


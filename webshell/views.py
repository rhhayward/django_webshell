from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.staticfiles.views import serve

from webshell.models import History, CmdType, Cwd

import subprocess
import os
from json import dumps, loads, JSONEncoder, JSONDecoder
import magic
import urllib
import time
import pickle

class PythonFileEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (list, dict, str, unicode, int, float, bool, type(None))):
            return JSONEncoder.default(self, obj)

        return obj.to_json()

def _get_cwd(request):
	if len(Cwd.objects.all()) <= 0:
		c = Cwd(user=request.user, cwd=os.getcwd())
		c.save()
	return Cwd.objects.all()[0]

def _set_cwd(request, cwd):
	c = _get_cwd(request)
	if cwd == "++":
		cwd = ".."
	cwd = cwd.replace('+', ' ')

	##  Turns out this breaks if the dir you're in is deleted out 
	##    from under you.
	#####if os.path.isdir(os.path.join(c.cwd, cwd)):
	c.cwd = os.path.abspath(os.path.join(c.cwd, cwd))
	c.save()

	return 1

def _save(request, fileName, fileContents):
	c = _get_cwd(request)
	f = open(os.path.join(c.cwd, fileName), 'w')
	f.write(fileContents.replace('\r\n', '\n'))
	f.close()

def isTextFile(fileName):
	if fileName.endswith(".py"):
		return True
	elif fileName.endswith(".pl"):
		return True
	elif fileName.endswith(".txt"):
		return True
	elif fileName.endswith(".html"):
		return True

	return False

@staff_member_required
def index(request):
	username=request.user.username
	return render_to_response('webshell/index.html', locals(), context_instance=RequestContext(request))

@staff_member_required
def execute(request):
        return render_to_response('webshell/execute.html', locals(), context_instance=RequestContext(request))

@staff_member_required
def _execute(request, command, cwdin):
	if cwdin == "":
		cwdin = os.getcwd()
	cmdtype = CmdType.objects.all()[0]

	if History.objects.filter(user=request.user, cmd_type=cmdtype, cmd_text=command, cmd_pwd=cwdin).exists():
		v = History.objects.get(user=request.user, cmd_type=cmdtype, cmd_text=command, cmd_pwd=cwdin)
		v.time_stamp=timezone.now()
		v.save()
	else:
		v = History(user=request.user, cmd_type=cmdtype, cmd_text=command, time_stamp=timezone.now(), cmd_pwd=cwdin)
		v.save()
	username=request.user.username

	out = None
	err = None
	if command.endswith("&"):
		subprocess.Popen(command, shell=True, cwd=cwdin)
	else:
		(out, err) = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, shell=True, cwd=cwdin).communicate(None)

	history_list = History.objects.all().order_by('time_stamp')
	er = ExecResult(out, err, history_list)
	return er

@staff_member_required
def history_delete(request, hid):
	try:
		v = History.objects.get(user=request.user, id=hid)
		v.delete()
	except:
		pass
		
	return history(request)
	
@staff_member_required
def history(request):
	username=request.user.username
	history_list = History.objects.all().order_by('time_stamp')
	return render_to_response('webshell/history.html', locals(), context_instance=RequestContext(request))

@staff_member_required
def set_cwd(request, cwd):
	_set_cwd(request, cwd)

	return file_manager(request)

@staff_member_required
def file_manager(request):
	c = _get_cwd(request)
	return _file_manager(request, c.cwd)

@staff_member_required
def _get_files(request, cwdin):
	username=request.user.username
	if cwdin == "":
		cwdin = os.getcwd()

	dirList = []
	try:
		dirList=os.listdir(cwdin)
	except:
		pass

	files = []
	### Add ".." by default
	f = File(os.path.abspath(os.path.join(cwdin,"..")), "..", "dir")
	files.append(f)

	### Here's what finally worked
	try:
		dirList = [f.decode('utf-8', 'ignore') for f in dirList]
	except:
		try:
			dirList = [unicode(f) for f in dirList]
		except:
			try:
				dirList = [urllib.quote(f.encode('utf8')) for f in dirList]
			except:
				dirList = []

	### Add everything else we find
	for fname in sorted(dirList):
		filePath = os.path.join(cwdin,urllib.unquote(fname))
		fileType = "file"
		if os.path.isdir(filePath):
			fileType = "dir"
		elif fname.lower().endswith(".png") or fname.lower().endswith(".jpg") or fname.lower().endswith(".gif"):
			fileType = "image"
		elif isTextFile(fname):
			fileType = "text"

		size = None
		try:
			size = os.path.getsize(filePath)
		except:
			pass

		dateModified = None
		try:
			dateModified = os.path.getmtime(filePath)
		except:
			pass

		#f = File(cwdin, urllib.quote_plus(fname), fileType, size, dateModified)
		f = File(cwdin, fname, fileType, size, dateModified)
		files.append(f)
	
	return files

@staff_member_required
def _get_history_list(request, cwdin):
	history_list = History.objects.all().order_by('time_stamp')
	return history_list
	
@staff_member_required
def _file_manager(request, cwdin):
	files = _get_files(request, cwdin)

	history_list = _get_history_list(request, cwdin)

	return render_to_response('webshell/file_manager.html', locals(), context_instance=RequestContext(request))

def _file_rm(request, fileName):
	try:
		fileName = fileName.replace('+', ' ')
		fileName = os.path.abspath(os.path.join(_get_cwd(request).cwd, fileName))
		if os.path.isdir(fileName):
			os.removedirs(fileName)
		else:
			os.remove(fileName)
	except:
		print "there was an error " + fileName
		return 0

	return 1

@staff_member_required
def file_rm(request):
	if request.method == 'POST':
		fileName = request.POST['fileName']
		print "has a filename:" + str(fileName)
		_delete(request, fileName)

		return file_manager(request)
	else:
		return file_manager(request)

@staff_member_required
def execute_ajax(request):
	cwd = _get_cwd(request).cwd
	if request.method == 'POST':
		cmd = request.POST['command']
		er = _execute(request, cmd, cwd)

		json_data = dumps({"HTTPRESPONSE":er.out})
		return HttpResponse(json_data, mimetype="application/json")
	else:
		json_data = dumps({"HTTPRESPONSE":False})
		return HttpResponse(json_data, mimetype="application/json")

@staff_member_required
def get_files_ajax(request):
	cwd = _get_cwd(request).cwd
	files = _get_files(request, cwd)
	json_data = dumps(files, cls=PythonFileEncoder)

	return HttpResponse(json_data, mimetype="application/json")

@staff_member_required
def set_cwd_ajax(request, dirName):
	response = _set_cwd(request, dirName)
	cwd = _get_cwd(request).cwd
	json_data = dumps({"HTTPRESPONSE":response, "cwd":cwd })
	return HttpResponse(json_data, mimetype="application/json")

def fix_fileName(fileName):
	fileName = fileName.replace('+', ' ')
	return fileName

@staff_member_required
def file_rm_ajax(request, fileName):
	fileName = fix_fileName(fileName)
	response = _file_rm(request, fileName)
	
	json_data = dumps({"HTTPRESPONSE":response})
	return HttpResponse(json_data, mimetype="application/json")

@staff_member_required
def editor_view(request, fileName):
	fileName = fix_fileName(fileName)
	cwd = _get_cwd(request).cwd

	fileContents = open(os.path.join(cwd, fileName)).read()
	return render_to_response('webshell/editor.html', locals(), context_instance=RequestContext(request))

@staff_member_required
def editor_save(request, fileName):
	if request.method == 'POST':
		fileContents = request.POST['fileContents']
		_save(request, fileName, fileContents)

	return editor_view(request, fileName)

@staff_member_required
def get_file(request, fileName):
	cwd = _get_cwd(request).cwd
	fileName = fileName.replace('+', ' ')

	fileContentType = 'application/octet-stream'
	if fileName.endswith(".png"):
		fileContentType = 'image/png'
	elif fileName.lower().endswith(".jpg"):
		fileContentType = 'image/jpg'
	elif fileName.endswith(".gif"):
		fileContentType = 'image/gif'
	elif isTextFile(fileName):
		fileContentType = 'text/plain'
	else:
		fileContentType = magic.from_file(os.path.join(cwd, fileName), mime=True)
	
	my_data = open(os.path.join(cwd, fileName)).read()
        response = HttpResponse(my_data, content_type=fileContentType)
	response['Content-Length'] = len(my_data)
	return response

class File:
        def __init__(self, path=None, name=None, fileType=None, size=None, dateModified=None):
		self.setPath(path)
		self.setName(name)
		self.setFileType(fileType)
		self.setSize(size)
		self.setDateModified(dateModified)

	def to_json(self):
		return {
			'name':self.name,
			'fileType':self.fileType,
			'size':self.size,
			'dateModified':self.dateModified
		}

	def setPath(self, path):
		self.path = path

	def setName(self, name):
		self.name = name

	def setFileType(self, fileType):
		self.fileType = fileType

	def setDateModified(self, dateModified):
		self.dateModified = time.strftime("%m/%d/%Y %I:%M:%S %p",time.localtime(dateModified))

	def setSize(self, size):
		if size == None:
			self.size = ""
		elif size < 1024:
			self.size = str(size) + "b"
		elif size < 1024*1024:
			self.size = str(size/1024) + "k"
		else:
			self.size = str(size/(1024*1024)) + "m"

class ExecResult:
	def __init__(self, out=None, err=None, history_list=None):
		self.setOut(out)
		self.setErr(err)
		self.setHistoryList(history_list)

	def setOut(self, out):
		self.out = out

	def setErr(self, err):
		self.err = err

	def setHistoryList(self, history_list):
		self.history_list = history_list

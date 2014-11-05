from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class CmdType(models.Model):
	def __unicode__(self):
		return self.description

	description = models.CharField(max_length=200)

class History(models.Model):
	def __unicode__(self):
		return self.user.username + ":" + self.cmd_text

	user = models.ForeignKey(User)
	cmd_type = models.ForeignKey(CmdType)
	cmd_text = models.CharField(max_length=2048)
	cmd_pwd  = models.CharField(max_length=2048)
	time_stamp = models.DateTimeField('time stamp')

class Cwd(models.Model):
	def __unicode__(self):
		return self.cwd

	cwd = models.CharField(max_length=20148)
	user = models.ForeignKey(User)

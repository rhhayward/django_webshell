from django.conf.urls import patterns, url

from webshell import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^history/$', views.history, name='history'),
    url(r'^history/delete/(\d+)$', views.history_delete, name='history'),
    url(r'^execute/(?P<command>.+)$', views.execute, name='execute'),
    url(r'^execute/$', views.execute, name='execute'),
    url(r'^editor/view/(?P<fileName>.+)$', views.editor_view, name='editor_view'),
    url(r'^editor/save/(?P<fileName>.+)$', views.editor_save, name='editor_save'),
    url(r'^file_manager/$', views.file_manager, name='file_manager'),
    url(r'^file_manager/delete/$', views.file_rm, name='file_rm'),
    url(r'^ajax/delete/(?P<fileName>.+)$', views.file_rm_ajax, name='file_rm_ajax'),
    url(r'^ajax/set_cwd/(?P<dirName>.+)$', views.set_cwd_ajax, name='set_cwd_ajax'),
    url(r'^ajax/get_files/$', views.get_files_ajax, name='get_files_ajax'),
    url(r'^ajax/execute/$', views.execute_ajax, name='execute_ajax'),
    url(r'^file_manager/get/(?P<fileName>.+)$', views.get_file, name='get_file'),
    url(r'^file_manager/set_cwd/(?P<cwd>.+)$', views.set_cwd, name='set_cwd'),
)


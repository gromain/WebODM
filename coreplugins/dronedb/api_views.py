import importlib
import requests
import os
from os import path

from requests.structures import CaseInsensitiveDict
from app import models, pending_actions
from app.plugins.views import TaskView
from app.plugins.worker import run_function_async
from app.plugins import get_current_plugin
from coreplugins.dronedb.ddb import DroneDB, verify_url

from worker.celery import app
from rest_framework.response import Response
from rest_framework import status

#from .platform_helper import get_all_platforms, get_platform_by_name

class ImportDatasetTaskView(TaskView):
    def post(self, request, project_pk=None, pk=None):
                        
        # Read form data
        ddb_url = request.data.get('ddb_url', None)
        #platform_name = request.data.get('platform', None)
        
        ds = get_current_plugin().get_user_data_store(request.user)
                
        registry_url = ds.get_string('registry_url', default="")
        username = ds.get_string('username', default="")
        password = ds.get_string('password', default="")
        
        # Make sure both values are set
        if ddb_url == None:
            return Response({'error': 'DroneDB url must be set.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Fetch the platform by name    
        ddb = DroneDB(registry_url, username, password)
                        
        # Verify that the folder url is valid    
        if ddb.verify_folder_url(ddb_url) == None:
            return Response({'error': 'Invalid URL'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the files from the folder
        files = ddb.import_from_folder(ddb_url)
        
        # Update the task with the new information
        task.console_output += "Importing {} images...\n".format(len(files))
        task.images_count = len(files)
        task.pending_action = pending_actions.IMPORT
        task.save()
        
        # Associate the folder url with the project and task
        combined_id = "{}_{}".format(project_pk, pk)
        get_current_plugin().get_global_data_store().set_string(combined_id, ddb_url)

        # Start importing the files in the background
        serialized = {'token': ddb.token, 'files': [file.serialize() for file in files]}
        run_function_async(import_files, task.id, serialized)

        return Response({}, status=status.HTTP_200_OK)

class CheckCredentialsTaskView(TaskView):
    def post(self, request):

        # Read form data
        hub_url = request.data.get('hubUrl', None)
        username = request.data.get('userName', None)
        password = request.data.get('password', None)

        # Make sure both values are set
        if hub_url == None or username == None or password == None:
            return Response({'error': 'All fields must be set.'}, status=status.HTTP_400_BAD_REQUEST)

        try:

            ddb = DroneDB(hub_url, username, password)

            return Response({'success': ddb.login()}, status=status.HTTP_200_OK)      

        except(Exception) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class OrganizationsTaskView(TaskView):
    def get(self, request):

        datastore = get_current_plugin().get_user_data_store(request.user)
        
        registry_url = datastore.get_string('registry_url')
        username = datastore.get_string('username')
        password = datastore.get_string('password')

        if registry_url == None or username == None or password == None:
            return Response({'error': 'Credentials must be set.'}, status=status.HTTP_400_BAD_REQUEST)

        try:

            ddb = DroneDB(registry_url, username, password)

            orgs = ddb.get_organizations()

            return Response(orgs, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DatasetsTaskView(TaskView):
    def get(self, request, org=None):

        if org == None:
            return Response({'error': 'Organization must be set.'}, status=status.HTTP_400_BAD_REQUEST)

        datastore = get_current_plugin().get_user_data_store(request.user)
        
        registry_url = datastore.get_string('registry_url')
        username = datastore.get_string('username')
        password = datastore.get_string('password')

        if registry_url == None or username == None or password == None:
            return Response({'error': 'Credentials must be set.'}, status=status.HTTP_400_BAD_REQUEST)

        try:

            ddb = DroneDB(registry_url, username, password)

            dss = ddb.get_datasets(org)

            return Response(dss, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class FoldersTaskView(TaskView):
    def get(self, request, org=None, ds=None):

        if org == None or ds == None:
            return Response({'error': 'Organization and dataset must be set.'}, status=status.HTTP_400_BAD_REQUEST)

        datastore = get_current_plugin().get_user_data_store(request.user)
        
        registry_url = datastore.get_string('registry_url')
        username = datastore.get_string('username')
        password = datastore.get_string('password')

        if registry_url == None or username == None or password == None:
            return Response({'error': 'Credentials must be set.'}, status=status.HTTP_400_BAD_REQUEST)

        try:

            ddb = DroneDB(registry_url, username, password)

            folders = ddb.get_folders(org, ds)

            return Response(folders, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class VerifyUrlTaskView(TaskView):
    def post(self, request):

        # Read form data
        url = request.data.get('url', None)

        if url == None:
            return Response({'error': 'Url must be set.'}, status=status.HTTP_400_BAD_REQUEST)

        datastore = get_current_plugin().get_user_data_store(request.user)
        
        registry_url = datastore.get_string('registry_url')
        username = datastore.get_string('username')
        password = datastore.get_string('password')

        if registry_url == None or username == None or password == None:
            return Response({'error': 'Credentials must be set.'}, status=status.HTTP_400_BAD_REQUEST)

        try:

            res = verify_url(url, username, password)            

            return Response({'count': res, 'success': True} if res else {'success': False}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # combined_id = "{}_{}".format(project_pk, pk)
        # folder_url = get_current_plugin().get_global_data_store().get_string(combined_id, default = None)

# class CheckUrlTaskView(TaskView):
#     def get(self, request, project_pk=None, pk=None):

#         # Assert that task exists
#         self.get_and_check_task(request, pk)

#         # Check if there is an imported url associated with the project and task
#         combined_id = "{}_{}".format(project_pk, pk)
#         folder_url = get_current_plugin().get_global_data_store().get_string(combined_id, default = None)

#         if folder_url == None:
#             return Response({}, status=status.HTTP_200_OK)
#         else:
#             return Response({'folder_url': folder_url}, status=status.HTTP_200_OK)

# class PlatformsVerifyTaskView(TaskView):
#     def get(self, request, platform_name):
#         # Read the form data
#         folder_url = request.GET.get('folderUrl', None)
        
#         # Fetch the platform by name
#         platform = get_platform_by_name(platform_name)
        
#         # Make sure that the platform actually exists
#         if platform == None:
#             return Response({'error': 'Failed to find a platform with the name \'{}\''.format(platform_name)}, status=status.HTTP_400_BAD_REQUEST)
        
#         # Verify that the folder url is valid    
#         folder = platform.verify_folder_url(folder_url)
#         if folder == None:
#             return Response({'error': 'Invalid URL'}, status=status.HTTP_400_BAD_REQUEST)
        
#         # Return the folder
#         return Response({'folder': folder.serialize()}, status=status.HTTP_200_OK)


# # class PlatformsTaskView(TaskView):
# #     def get(self, request):
# #         # Fetch and return all platforms
# #         platforms = get_all_platforms()
# #         return Response({'platforms': [platform.serialize(user = request.user) for platform in platforms]}, status=status.HTTP_200_OK)


def import_files(task_id, carrier):
    import requests
    from app import models
    from app.plugins import logger

    files = carrier.files
    
    headers = CaseInsensitiveDict()

    if carrier.token != None:
        headers['Authorization'] = 'Token ' + carrier['token']

    def download_file(task, file):
        path = task.task_path(file['name'])
        download_stream = requests.get(file['url'], stream=True, timeout=60, headers=headers)

        with open(path, 'wb') as fd:
            for chunk in download_stream.iter_content(4096):
                fd.write(chunk)
        
        models.ImageUpload.objects.create(task=task, image=path)

    logger.info("Will import {} files".format(len(files)))
    task = models.Task.objects.get(pk=task_id)
    task.create_task_directories()
    task.save()
    
    try:
        downloaded_total = 0
        for file in files: 
            download_file(task, file)
            task.check_if_canceled()
            models.Task.objects.filter(pk=task.id).update(upload_progress=(float(downloaded_total) / float(len(files))))
            downloaded_total += 1

    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        raise NodeServerError(e)

    task.refresh_from_db()
    task.pending_action = None
    task.processing_time = 0
    task.partial = False
    task.save()

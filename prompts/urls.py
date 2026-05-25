from django.urls import path

from . import views

app_name = 'prompts'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/tree/', views.prompt_tree, name='tree'),
    path('api/prompt/', views.prompt_detail, name='prompt-detail'),
    path('api/prompt/save/', views.save_prompt_version, name='save-version'),
    path('api/prompt/channel/', views.assign_prompt_channel, name='assign-channel'),
    path('api/prompt/channel/delete/', views.delete_prompt_channel, name='delete-channel'),
    path('api/prompt/version/delete/', views.delete_prompt_version, name='delete-version'),
    path('api/prompt/delete/', views.delete_prompt, name='delete-prompt'),
    path('api/prompt/test/', views.test_prompt, name='test-prompt'),
    path('api/prompt/test/inline/', views.test_prompt_inline, name='test-prompt-inline'),
    path('api/departments/sub/', views.sub_department_list, name='sub-departments'),
]
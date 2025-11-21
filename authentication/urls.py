from django.urls import path
from . import views
from . import ui_views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('change_password/', views.change_password, name='change_password'),
    # Logo 图片直出，绕过 /static
    path('logo.png', views.logo_png, name='logo_png'),
    # UI 登录/退出
    path('ui/login/', ui_views.login_page, name='login_page'),
    path('ui/logout/', ui_views.logout_page, name='logout_page'),
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    # 管理员设置用户配额
    path('quota/<int:user_id>/', views.set_user_quota, name='set_user_quota'),
    # 组织与成员管理 API
    path('orgs/', views.org_list, name='org_list'),
    path('orgs/create/', views.org_create, name='org_create'),
    path('orgs/<int:org_id>/members/', views.org_members, name='org_members'),
    path('orgs/<int:org_id>/members/add/', views.org_member_add, name='org_member_add'),
    path('orgs/<int:org_id>/members/<int:member_id>/update/', views.org_member_update, name='org_member_update'),
    path('orgs/<int:org_id>/members/<int:member_id>/remove/', views.org_member_remove, name='org_member_remove'),

    # 组织与成员管理 UI 页面
    path('orgs/ui/', ui_views.org_list_page, name='org_list_page'),
    path('orgs/ui/create/', ui_views.org_create_page, name='org_create_page'),
    path('orgs/ui/<int:org_id>/members/', ui_views.org_members_page, name='org_members_page'),
]
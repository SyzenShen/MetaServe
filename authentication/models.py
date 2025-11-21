from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    """自定义用户管理器，使用邮箱创建用户"""
    
    def create_user(self, email, password=None, **extra_fields):
        """创建普通用户"""
        if not email:
            raise ValueError('邮箱地址是必需的')
        email = self.normalize_email(email)
        # 使用邮箱作为用户名
        extra_fields.setdefault('username', email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """创建超级用户"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('超级用户必须设置 is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('超级用户必须设置 is_superuser=True')
            
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """自定义用户模型，使用邮箱作为用户名"""
    email = models.EmailField(unique=True, verbose_name='邮箱地址')
    # 每个用户的存储限额（字节）。默认 50 GB
    storage_quota = models.BigIntegerField(
        default=50 * 1024 * 1024 * 1024,
        verbose_name='存储限额（字节）'
    )
    
    # 使用自定义用户管理器
    objects = CustomUserManager()
    
    # 使用邮箱作为用户名字段
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # 创建超级用户时需要的额外字段
    
    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
    
    def __str__(self):
        return self.email


class Organization(models.Model):
    """组织模型，用于用户层级与内部权限判定"""
    name = models.CharField(max_length=255, unique=True, verbose_name='组织名称')
    owner = models.ForeignKey('authentication.CustomUser', on_delete=models.CASCADE, related_name='owned_organizations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '组织'
        verbose_name_plural = '组织'

    def __str__(self):
        return self.name


class Membership(models.Model):
    """组织成员关系，带角色"""
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey('authentication.CustomUser', on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('organization', 'user')
        verbose_name = '组织成员'
        verbose_name_plural = '组织成员'

    def __str__(self):
        return f"{self.organization.name} - {self.user.email} ({self.role})"

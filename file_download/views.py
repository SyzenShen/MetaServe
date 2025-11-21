import os
import mimetypes
import urllib.parse
import zipfile
import tempfile
from django.http import HttpResponse, Http404, StreamingHttpResponse, FileResponse
from file_upload.models import File, Folder
from file_upload.permission_utils import can_view_or_download_file
from file_upload.permissions import IsFolderReadable

# Create your views here.
# Case 1: simple file download, very bad
# Reason 1: loading file to memory and consuming memory
# Can download all files, including raw python .py codes


def file_download(request, file_path):
    # do something...
    with open(file_path) as f:
        c = f.read()
    return HttpResponse(c)


# Case 2 Use HttpResponse to download a small file
# Good for txt, not suitable for big binary files
def media_file_download(request, file_path):
    with open(file_path, 'rb') as f:
        try:
            response = HttpResponse(f)
            response['content_type'] = "application/octet-stream"
            response['Content-Disposition'] = 'attachment; filename=' + os.path.basename(file_path)
            return response
        except Exception:
            raise Http404


# Case 3 Use StreamingHttpResponse to download a large file
# Good for streaming large binary files, ie. CSV files
# Do not support python file "with" handle. Consumes response time
def stream_http_download(request, file_path):
    try:
        response = StreamingHttpResponse(open(file_path, 'rb'))
        response['content_type'] = "application/octet-stream"
        response['Content-Disposition'] = 'attachment; filename=' + os.path.basename(file_path)
        return response
    except Exception:
        raise Http404


# Case 4 Use FileResponse to download a large file
# It streams the file out in small chunks
# It is a subclass of StreamingHttpResponse
# Use @login_required to limit download to logined users
def file_response_download1(request, file_path):
    try:
        response = FileResponse(open(file_path, 'rb'))
        response['content_type'] = "application/octet-stream"
        response['Content-Disposition'] = 'attachment; filename=' + os.path.basename(file_path)
        return response
    except Exception:
        raise Http404


# Case 5 Limit file download type - recommended
def file_response_download(request, file_path):
    # 强制走对象级权限：通过 File 记录查找并校验
    try:
        file_obj = File.objects.get(file=file_path)
    except File.DoesNotExist:
        # 兼容传入绝对路径或存储路径的场景，尝试按文件名匹配
        try:
            base = os.path.basename(file_path)
            file_obj = File.objects.filter(original_filename=base).first()
            if not file_obj:
                file_obj = File.objects.filter(file__icontains=base).first()
            if not file_obj:
                raise File.DoesNotExist
        except File.DoesNotExist:
            raise Http404

    if not can_view_or_download_file(request.user, file_obj):
        raise Http404

    real_path = file_obj.file.path
    if not os.path.exists(real_path):
        raise Http404

    # 双重防护：限制敏感扩展名
    ext = os.path.basename(real_path).split('.')[-1].lower()
    if ext in ['py', 'db', 'sqlite3']:
        raise Http404

    response = FileResponse(open(real_path, 'rb'))
    response['content_type'] = "application/octet-stream"
    response['Content-Disposition'] = 'attachment; filename=' + (file_obj.original_filename or os.path.basename(real_path))
    return response


# New: Download by File ID with RFC 5987 filename* for UTF-8
def file_download_by_id(request, file_id):
    try:
        file_obj = File.objects.get(id=file_id)
        # 对象级权限校验
        if not can_view_or_download_file(request.user, file_obj):
            raise Http404("File not found")
        if not file_obj.file or not os.path.exists(file_obj.file.path):
            raise Http404("File not found")

        file_path = file_obj.file.path
        display_name = file_obj.original_filename or os.path.basename(file_path)

        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'

        response = FileResponse(open(file_path, 'rb'), content_type=content_type)

        # RFC 5987: filename* using UTF-8 percent-encoding
        utf8_name = urllib.parse.quote(display_name, safe='')
        # ASCII fallback: try latin-1; if fails, replace non-ASCII
        try:
            ascii_fallback = display_name.encode('latin-1').decode('latin-1')
        except UnicodeEncodeError:
            ascii_fallback = ''.join(ch if ord(ch) < 128 else '_' for ch in display_name)

        response['Content-Disposition'] = (
            f"attachment; filename={ascii_fallback}; filename*=UTF-8''{utf8_name}"
        )
        return response
    except File.DoesNotExist:
        raise Http404("File not found")


def folder_download_by_id(request, folder_id):
    """
    Download a folder as a ZIP archive containing all files and subfolders
    """
    try:
        folder = Folder.objects.get(id=folder_id)
        # 简单的对象级权限：仅允许访问自己文件夹
        if getattr(folder, 'user_id', None) != getattr(request.user, 'id', None):
            raise Http404("Folder not found")
        
        # Create a temporary file for the ZIP
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_file.close()
        
        try:
            # Create ZIP file
            with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                _add_folder_to_zip(zipf, folder, folder.name, user=request.user)
            
            # Prepare response
            folder_name = folder.name or f"folder_{folder_id}"
            zip_filename = f"{folder_name}.zip"
            
            # RFC 5987: filename* using UTF-8 percent-encoding
            utf8_name = urllib.parse.quote(zip_filename, safe='')
            try:
                ascii_fallback = zip_filename.encode('latin-1').decode('latin-1')
            except UnicodeEncodeError:
                ascii_fallback = ''.join(ch if ord(ch) < 128 else '_' for ch in zip_filename)
            
            response = FileResponse(
                open(temp_file.name, 'rb'),
                content_type='application/zip'
            )
            response['Content-Disposition'] = (
                f"attachment; filename={ascii_fallback}; filename*=UTF-8''{utf8_name}"
            )
            
            # Clean up temp file after response is sent
            def cleanup():
                try:
                    os.unlink(temp_file.name)
                except OSError:
                    pass
            
            # Schedule cleanup when response is closed
            response.close = cleanup
            
            return response
            
        except Exception as e:
            # Clean up temp file on error
            try:
                os.unlink(temp_file.name)
            except OSError:
                pass
            raise Http404(f"Error creating ZIP file: {str(e)}")
            
    except Folder.DoesNotExist:
        raise Http404("Folder not found")


def _add_folder_to_zip(zipf, folder, base_path="", user=None):
    """
    Recursively add folder contents to ZIP file with per-file permission filtering
    """
    # Add all files in this folder, applying object-level permissions
    for file_obj in folder.files.all():
        try:
            if not can_view_or_download_file(user, file_obj):
                continue
            if not file_obj.file or not os.path.exists(file_obj.file.path):
                continue
            # Block sensitive extensions inside ZIP as an extra safeguard
            ext = os.path.basename(file_obj.file.path).split('.')[-1].lower()
            if ext in ['py', 'db', 'sqlite3']:
                continue
            file_path_in_zip = os.path.join(base_path, file_obj.original_filename or os.path.basename(file_obj.file.path))
            zipf.write(file_obj.file.path, file_path_in_zip)
        except Exception:
            # Skip any problematic file silently to avoid breaking entire archive
            continue
    
    # Recursively add subfolders (only traverse if the user can read the folder)
    for subfolder in folder.subfolders.all():
        if getattr(subfolder, 'user_id', None) != getattr(user, 'id', None):
            # Currently only owner traversal; extend here for org/global policies later
            continue
        subfolder_path = os.path.join(base_path, subfolder.name)
        _add_folder_to_zip(zipf, subfolder, subfolder_path, user=user)


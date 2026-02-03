# Permission System Architecture

## 1. Overview
MetaServe employs a **Hybrid Authorization Model** combining:
- **RBAC (Role-Based Access Control)**: For organizational hierarchy (Owner, Admin, Member).
- **ACL (Access Control Lists)**: For fine-grained file sharing (FileShare).
- **ABAC (Attribute-Based Access Control)**: For access levels (Public, Internal, Restricted).

## 2. Access Levels

| Level | Scope | Who has access? |
| :--- | :--- | :--- |
| **Public** | Global | Any authenticated user (system-wide). |
| **Internal** | Organization | Users in the **same organization** as the file owner. |
| **Restricted** | Private | Only the **Owner** + Explicitly shared users (via FileShare). |

## 3. Conflict Resolution (Precedence)
**Rule**: "Most Restrictive Precedence" (最严格优先原则)
- If a file is in an Organization Folder, it **MUST** be `Restricted`.
- Permissions flow: Folder -> File. A file cannot be `Public` if its parent folder is `Private`.

## 4. Key Components

### 4.1 Models
- **File**: Stores `access_level` (Public/Internal/Restricted).
- **FileShare**: Stores explicit grants (`can_download`, `can_edit_metadata`) to User or Organization.
- **Membership**: Links User to Organization with a Role.

### 4.2 Utility Functions (`permission_utils.py`)
- `can_view_or_download_file(user, file)`: The master gatekeeper.
- `can_edit_file_metadata(user, file)`: For metadata updates.
- `can_delete_file(user, file)`: Owner or Org Admin only.

## 5. Security Enforcements
1. **Zero-copy Manifest**: Physical paths are only exposed to users with valid system accounts; file permissions set to `0o644` (Owner RW, Group R, Others R) or stricter based on deployment config.
2. **API Gatekeeper**: All HTTP downloads are authorized via Django middleware/views before streaming.

// Codes of the permissions a role is made of. The list lives on the backend
// (`apps/access/permissions.py`, also served by `GET /permissions/`); these
// are only the codes the interface itself checks.
export const PERMISSION = {
  companyEdit: 'company.edit',
  companyMembers: 'company.members',
  companyRoles: 'company.roles',
  companyPipeline: 'company.pipeline',
  projectCreate: 'project.create',

  projectEdit: 'project.edit',
  projectDelete: 'project.delete',
  projectMembers: 'project.members',
  feedView: 'feed.view',

  shotCreate: 'shot.create',
  shotEdit: 'shot.edit',
  shotDelete: 'shot.delete',
  shotImport: 'shot.import',
  groupManage: 'group.manage',

  taskCreate: 'task.create',
  taskEdit: 'task.edit',
  taskDelete: 'task.delete',
  taskUpdateOwn: 'task.update_own',

  versionUpload: 'version.upload',
  versionDelete: 'version.delete',
  versionDeleteOwn: 'version.delete_own',

  chatWrite: 'chat.write',
  chatEditAny: 'chat.edit_any',
} as const

// The permissions that act through the role in the company, not in a project.
export const COMPANY_LEVEL_CODES = [
  PERMISSION.companyEdit,
  PERMISSION.companyMembers,
  PERMISSION.companyRoles,
  PERMISSION.companyPipeline,
  PERMISSION.projectCreate,
  'company.delete',
] as const

export type PermissionCode = (typeof PERMISSION)[keyof typeof PERMISSION]

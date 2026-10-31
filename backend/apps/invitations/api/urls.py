from dmr.routing import Router, path

from .views import (
    CompanyInvitationListController,
    InvitationDetailController,
    InvitationRenewController,
    InviteAcceptController,
    InviteInfoController,
    InviteRegisterController,
    ProjectInvitationController,
)


router = Router(
    "",
    [
        path(
            "companies/<int:company_id>/invitations/",
            CompanyInvitationListController.as_view(),
            name="company-invitation-list",
        ),
        path(
            "projects/<int:project_id>/invitations/",
            ProjectInvitationController.as_view(),
            name="project-invitation-create",
        ),
        path(
            "invitations/<int:invitation_id>/",
            InvitationDetailController.as_view(),
            name="invitation-detail",
        ),
        path(
            "invitations/<int:invitation_id>/renew/",
            InvitationRenewController.as_view(),
            name="invitation-renew",
        ),
        path("invite/<str:token>/", InviteInfoController.as_view(), name="invite-info"),
        path(
            "invite/<str:token>/register/",
            InviteRegisterController.as_view(),
            name="invite-register",
        ),
        path(
            "invite/<str:token>/accept/",
            InviteAcceptController.as_view(),
            name="invite-accept",
        ),
    ],
)

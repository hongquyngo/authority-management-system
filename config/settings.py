APP_CONFIG = {
    'title': 'Authority Management System',
    'icon': '🔐',
    'version': '1.0.0',
    'modules': {
        'approval': {
            'enabled': True,
            'name': 'Approval Authorities',
            'icon': '👥',
            'description': 'Manage approval permissions'
        },
        'data_access': {
            'enabled': False,
            'name': 'Data Access Control',
            'icon': '🔍',
            'description': 'Control data access permissions'
        }
    },
    'theme': {
        'primary_color': '#FF6B6B',
        'success_color': '#51CF66',
        'warning_color': '#FFD93D',
        'error_color': '#FF6B6B',
        'info_color': '#4ECDC4'
    }
}

# User roles
USER_ROLES = {
    'admin': {
        'name': 'Administrator',
        'permissions': ['view', 'add', 'edit', 'delete', 'import', 'export', 'settings']
    },
    'manager': {
        'name': 'Manager',
        'permissions': ['view', 'add', 'edit', 'import', 'export']
    },
    'viewer': {
        'name': 'Viewer',
        'permissions': ['view', 'export']
    }
}
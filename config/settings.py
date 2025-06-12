# config/settings.py

APP_CONFIG = {
    'title': 'Authority Management System',
    'version': '1.0.0',
    'icon': '🔐',
    'modules': {
        'approval': {
            'name': 'Approval Authorities',
            'icon': '👥',
            'enabled': True,
            'description': 'Manage approval authorities for different types and companies'
        },
        'users': {
            'name': 'User Management',
            'icon': '👤',
            'enabled': True,
            'description': 'Manage system users, roles, and permissions'
        },
        'visibility': {
            'name': 'Data Visibility',
            'icon': '👁️',
            'enabled': False,
            'description': 'Control data access and visibility rules'
        }
    }
}
from setuptools import setup

setup(
    name='Chess',
    options={
        'build_apps': {
            # Build Chess.exe as a GUI application
            'gui_apps': {
                'Chess': 'main.py',
            },

            # Set up output logging, important for GUI apps!
            'log_filename': '$USER_APPDATA/Chess/output.log',
            'log_append': False,

            # Specify which files are included with the distribution
            'include_patterns': [
                '**/*.jpg',
                '**/*.egg',
                '**/*.mp3',
                '**/*.json',
                '**/*.bam',
            ],
            
            # Exclude user-specific files from the packaged executable
            'exclude_patterns': [
                'config.json',
                'saves/*',
            ],

            # Include the OpenGL renderer and OpenAL audio plug-in
            'plugins': [
                'pandagl',
                'p3openal_audio',
                'p3ffmpeg',
            ],

            "icons": {
                # The key needs to match the key used in gui_apps/console_apps.
                # Alternatively, use "*" to set the icon for all apps.
                "Chess": ["panda3d-logo.png"],
            },
        }
    }
)

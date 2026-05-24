from setuptools import setup, find_packages

setup(
    name='lumina-annotator',
    version='1.1.0',
    description='A modern, modular multi-modal annotation tool for CV engineers.',
    author='Tentellect',
    packages=find_packages(),
    install_requires=[
        'Pillow>=9.0.0'
    ],
    entry_points={
        'console_scripts': [
            'lumina = src.main:main',
        ],
    },
    python_requires='>=3.7',
)

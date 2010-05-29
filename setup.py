# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name = "django-imagequery",
    version = "0.1-dev",
    author_email = "david.danier@team23.de",
    url = "http://bitbucket.org/ddanier/django-imagequery",
    
    packages = find_packages(exclude=[
        'example',
        'example.*'
    ]),
    package_data = {
        'imagequery.tests': [
            'samplefonts/*.ttf',
            'sampleimages/*.png',
            'sampleimages/*.jpg',
            'sampleimages/results/*.png',
            'sampleimages/results/*.jpg',
        ],
    },
    license = "BSD License",
    keywords = "django imagequery PIL",
    description = "Image manipulation written like well known QuerySet operations",
    install_requires=[
        'setuptools',
        'Django',
    ],
    classifiers = [
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
        'Topic :: Utilities',
    ],
    zip_safe=False,
)


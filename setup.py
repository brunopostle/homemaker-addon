from setuptools import setup, find_packages

setup(
    name='homemaker',
    version='0.1.0',
    description='Homemaker add-on',
    author='Bruno Postle',
    author_email='bruno@postle.net',
    url='https://github.com/brunopostle/homemaker-addon',
    license="GPLv3",
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    packages=find_packages(include=['topologist', 'topologist.*']),
    install_requires=['topologicPy'],
)

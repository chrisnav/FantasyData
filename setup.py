from setuptools import find_packages, setup

setup(
    name='FantasyData',
    packages=find_packages(include=['fantasydata']),
    version='0.1.0',
    description='A package to retreive and manage fantasy football data',
    url = 'https://github.com/chrisnav/FantasyData',
    author='Christian Øyn Naversen',
    author_email='christian.oyn.naversen@gmail.com',
    install_requires=['pandas>=1.3.2','requests','numpy>=1.20.2','statsmodels>=0.12.2'],
    license='MIT',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows :: Windows 10',        
        'Programming Language :: Python :: 3.9',
    ],    
)
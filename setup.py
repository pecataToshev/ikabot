import setuptools

from ikabot import __version__

setuptools.setup(
    name="ikabot",
    version=__version__,
    author="Petar Toshev",
    author_email="pecata.toshev+ikabot@gmail.com",
    license='MIT',
    description="A bot for ikariam",
    url="https://github.com/pecataToshev/ikabot",
    include_package_data=True,
    packages=setuptools.find_packages(),
    install_requires=[
        'requests',
        'requests[socks]',
        'psutil',
        'beautifulsoup4',
        'yoyo-migrations',
    ],
    entry_points={
        'console_scripts': ['ikabot=ikabot.__main__:main'],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License"
    ],
)

import setuptools

setuptools.setup(
    name="ikabot",
    version='2024.0109.dev094702',
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
        'cryptography',
        'psutil',
        'beautifulsoup4',
    ],
    entry_points={
        'console_scripts': ['ikabot=ikabot.command_line:main'],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License"
    ],
)

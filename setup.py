from setuptools import setup

setup(name='smt2hr',
      version='0.1',
      description='Convert Smtlib2 to human readable format',
      url='http://github.com/R3x/smt2hr',
      author='Siddharth Muralee',
      author_email='siddharth.muralee@gmail.com',
      license='MIT',
      packages=['smt2hr'],
      scripts=['bin/smtconv'],
      install_requires=[
          'pysmt',
      ],
      zip_safe=False)
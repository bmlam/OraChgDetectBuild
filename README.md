# OraChgDetectBuild

When working on a Oracle database application projects, one may have to create or change a handful or dozens table scripts, store procedure scripts, DML scripts. All these scripts are considered child scripts. And they need to be packaged into deployment deliverables. For example you want to include all the scripts pertaining to one schema, in a given order, into one single schema master SQL script. Since SQPLUS is the de facto deployment tool for Oracle and most shops use the Windows client version thereof, it makes sense also to generate a .BAT script to fire up SQLPLUS and invoke the master script.

mk_install_lines.py serves exactly this purpose. Assuming that the scripts are organized in a predefined folder structure and the file tree is under git revision control, user just needs to provide the base commit hash, the python script will figure out which scripts have been added or modified since that commit and compose one master SQL and one .BAT script per schema. The assumption is that the first level subdirectory is named the same as the schema, the second-level subdirectory is the script type, for example table scripts, DML scripts, package scripts. So if scripts from several schemata need to be deployed, one pair of .SQL and .BAT script will be created per schema. 

The ordering of the child scripts is achieved by a user-customizable SQL master script template. Run 

mk_install_lines.py -h 

to see options available.

Another concern when shipping deliverables is to determine which changes exist between 2 versions of a database object such as function, package body.

quickDiff.py is an attempt to provide a uniform formatting of stored procedure code so that 2 versions can be compared more conveniently, despite the fact that 2 developers may have formatted the 2 versions differently. Suppose these 2 versions have been compiled into 2 different databases. After extracting the 2 versions, one would have to deal with diffs due to intentional changes, but also due to formatting style differences. For this reason, the .py script can extract the same stored procedure from 2 different databases and store them on file, one version in the as-is format, the other version reformatted. If the 2 versions from the 2 databases have been compiled after being formatted with the same style, then it is best to compare the 2 versions in their as-is (original) presentation. Otherwise, it is better to compare the 2 versions in the reformatted presentation. The result of the reformatting by the .py script is really ugly, hence the reformatted output file has the suffix "ugly" in its name. Suppose you have extracted function MY_FUNC from database foo and bar. Then you should find 4 scripts in the temp output directory:

my_func-foo-original.sql
my_func-bar-original.sql
my_func-foo-ugly.sql
my_func-bar-ugly.sql

You can use your favorite diff-tool to peruse the changes. Run 

quickDiff.py -h 

to see options available.

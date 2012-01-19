# intemp.py: Execute a program in a temporary directory

This program aims to solve one of the common problems with cluster
computing: sometimes your jobs die, but they leave incomplete versions
of the appropriate output files behind, and you have to inspect each
outfile closely in order to determine whether it is complete or not.

With intemp.py, your program will run in a temporary directory and
produce its output files there. When the program exits successfully
(i.e. with a zero exit code), everything in the temporary directory
will be copied to the real output directory. So now you know that any
file in the output directory must be a complete output file produced
by a successful run of your program.

## Download

* Option A: Clone this repository on Github:

      $ git clone https://github.com/DarwinAwardWinner/intemp.git

* Option B: Download the latest version [here](https://raw.github.com/DarwinAwardWinner/intemp/master/intemp.py)

      $ wget https://raw.github.com/DarwinAwardWinner/intemp/master/intemp.py

Either way, you need to put it in your `$PATH` and ensure that it is marked executable.

## Usage

Suppose you want to run a command that takes an input file name with
`-i` and an output file name with `-o`, like this:

    $ mycommand -i input.txt -o output.txt

In the simplest case, you can run it with intemp.py by doing the
following:

    $ intemp.py -- mycommand -i /absolute/path/to/input.txt -o output.txt

Notice that you must specify *absolute* paths to all input files,
because you don't know what directory your program will run in. On the
other hand, you should specify *relative* paths to output files, so
that these files will be created in the temporary directory.

## Example

If you want a simple example with which to test intemp.py, try this command:

    $ echo hello | tee output.txt

To run this with intemp.py, do the following:

    $ echo hello | intemp.py tee output.txt

Notice that only the portion of the command that produces the output
file should be run with intemp.py. Notice also that `echo hello >
output.txt` would not be suitable, because this uses the shell
redirection operator `>` to create the output file. Thus the shell
itself creates the output file, not the command, so running the
command with intemp.py will have no effect.

## More

See the help text for more information, particular regarding
command-line options. There are options to save the temporary
directory, and to choose where the temporary directory is created, as
well as an option to select the directory where the output files will
be copied upon completion.

## Optimization

In order to get the best performance, you should specify a temporary
directory on the same filesystem as the true output directory, and you
should not specify `-p always`. This will allow intemp.py to *rename*
your output files to their final destinations instead of copying.

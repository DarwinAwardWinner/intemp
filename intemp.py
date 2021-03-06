#!/usr/bin/env python

import plac
import tempfile
import os
import os.path
import sys
import subprocess
import pipes
from shutil import copy2 as copy_file, move as move_file, copytree as copy_tree, rmtree as rm_tree

# tempfile.gettempdir seems broken on some systems. This is a
# workaround to actually use the environment variables when they are
# set.
def gettempdir():
    for var in ('TMP', 'TEMP'):
        val = os.getenv(var)
        if val:
            return val
    else:
        return tempfile.gettempdir()

def shellquote(string):
    if string == "":
        return '""'
    else:
        return pipes.quote(string)

def list2cmdline(cmdlist):
    return " ".join(shellquote(x) for x in cmdlist)

def ensure_nonexistent(dst, filenames, delete=False):
    """Ensure that each file does not exist in destination dir.

    If delete is False, then any files found to exist will raise an
    IOError. If delete is True, then any files found will be deleted."""
    for f in filenames:
        destfile = os.path.join(dst, f)
        if os.path.lexists(destfile):
            if delete:
                if os.path.isdir(destfile):
                    rm_tree(destfile)
                else:
                    os.unlink(destfile)
            else:
                raise IOError("Destination file %s already exists in %s" % (f, dst))

def do_sync(src, dst, overwrite=False, move=False, quiet=False):
    """Copy all files from src to dst.

    If overwrite is True, then existing files and directories in the
    destination directory will be replaced if there is a file or
    directory in the source directory with the same name.

    If move is True, then files will be moved instead of copied. This
    is a useful optimization if the source directory will be deleted
    afterward anyway."""
    filenames = os.listdir(src)
    ensure_nonexistent(dst, filenames, delete=overwrite)
    for f in filenames:
        srcfile = os.path.join(src, f)
        dstfile = os.path.join(dst, f)
        if move:
            if not quiet:
                print "Move %s to %s" % (f, dst)
            move_file(srcfile, dstfile)
        elif os.path.isdir(srcfile):
            if not quiet:
                print "Copy dir %s to %s" % (f, dst)
            copy_tree(srcfile, dstfile, symlinks=True)
        else:
            if not quiet:
                print "Copy %s to %s" % (f, dst)
            copy_file(srcfile, dstfile)

def directory(x):
    """Resolve symlinks, then return the result if it is a directory.

    Otherwise throw an error."""
    path = os.path.realpath(x)
    if not os.path.isdir(path):
        if path == x:
            msg = "Not a directory: %s" % x
        else:
            msg = "Not a directory: %s -> %s" % (x, path)
        raise TypeError(msg)
    else:
        return path

@plac.annotations(
    # arg=(helptext, kind, abbrev, type, choices, metavar)
    command=("The command to execute. This is best specified last after all options and a double dash: --", "positional"),
    arg=("The arguments to the command. Specified after the command itself.", "positional"),
    target_dir=("The directory where output files will be moved after the program exits successfully. This directory must already exist. By default, this is the current working directory.", "option", "d", directory, None, "DIR"),
    temp_dir=("The command will be run in an empty subdirectory of this directory. After completion, all files (and directories) produced in the the subdirectory will be moved to the target directory. You can also use the TEMP or TMP environment variables to specify this. Note that a relative path will be relative to the target directory", "option", "t", directory),
    preserve_temp_dir=("When to preserve the temporary directory after completion. By default, the temporary directory is preserved only if the command fails.", "option", "p", str, ("always", "never", "failure"), 'always|never|failure'),
    overwrite=("Overwrite files in destination directory.", "flag", "o"),
    quiet=("Produce no output other than what the command itself produces", "flag", "q"),
    stdin_file=("Read the command's standard input from this file. This and the next two options are meant as a replacement for shell redirection.", "option", "I", str, None, 'FILE'),
    stdout_file=("Redirect the command's standard output to this file. A relative path will be relative to the temporary directory.", "option", "O", str, None, 'FILE'),
    stderr_file=("Redirect the command's standard error stream to this file. A relative path will be relative to the temporary directory. This can be the same path as the output file, in which case both stderr and stdout will be redirected to the same file.", "option", "E", str, None, 'FILE'),
    )
def main(command, target_dir=os.getcwd(), temp_dir=gettempdir(), overwrite=False,
         preserve_temp_dir="failure", quiet=False, stdin_file=None,
         stdout_file=None, stderr_file=None, *arg):
    """Run a command in a temporary directory.

    If the command succeeds, then the contents of the temporary
    directory will be moved to the target directory (default pwd). If
    the command fails, the files will remain in the temporary
    directory (which may or may not be deleted). This bahavior ensures
    that only finished output files from successful commands will be
    put into the target directory, even if the command produces output
    files bit by bit and leaves incomplete output files upon failure.

    To separate options intended for intemp from those intended for
    the command itself, put a double dash by itself before the
    command, like this:

    intemp [intemp options here] -- command [command's options here] arg1 arg2 ...

    IMPORTANT: Since the specified program is run in a temporary
    directory, all paths to input files should be given as absolute
    paths, not relative ones. On the other hand, specifying relative
    paths for output files is recommended, since this will produce the
    output files in the temporary directory."""
    work_dir = None
    success = False
    try:
        work_dir = tempfile.mkdtemp(dir=os.path.join(target_dir, temp_dir))
        full_command = (command,) + arg
        if not quiet:
            print "Running in %s" % work_dir
            print "Command: %s" % list2cmdline(full_command)
        stdin=open(stdin_file, "r") if stdin_file is not None else None

        # Canonicalize paths
        stdout_file = os.path.realpath(os.path.join(work_dir, stdout_file)) if stdout_file else None
        stderr_file = os.path.realpath(os.path.join(work_dir, stderr_file)) if stderr_file else None

        if stdout_file:
            stdout = open(os.path.join(work_dir, stdout_file), "w")
        else:
            stdout = None

        if stderr_file == stdout_file:
            stderr = stdout
        elif stderr_file:
            stderr = open(os.path.join(work_dir, stderr_file), "w")
        else:
            stderr = None

        retval = subprocess.call(full_command, cwd=work_dir,
                                 stdin=stdin, stdout=stdout, stderr=stderr)
        for f in stdin, stdout, stderr:
            if f is not None:
                f.close()
        success = retval == 0

        if success:
            if not quiet:
                print "Command successful: %s" % list2cmdline(full_command)
            try:
                do_sync(src=work_dir, dst=target_dir, overwrite=overwrite, move=preserve_temp_dir != 'always', quiet=quiet)
            except IOError:
                success = False
                if not quiet:
                    print "Failed to copy result files to target dir"
        else:
            if not quiet:
                print "Command failed with return code %s: %s" % (retval, list2cmdline(full_command))
    except KeyboardInterrupt:
        success = False
        retval = 1
        if not quiet:
            print "\nJob canceled by Control + C."
        else:
            # Print a newline to make sure the '^C' that appears in
            # the terminal does not mess up the prompt.
            print "\n",
    finally:
        if not work_dir:
            pass
        elif not os.path.isdir(work_dir):
            pass
        else:
            if success:
                preserve = preserve_temp_dir == 'always'
                adjective = "successful"
                verb = "preserving" if preserve else "cleaning"
            else:
                preserve = preserve_temp_dir != 'never'
                adjective = "failed"
                verb = "preserving" if preserve else "deleting"
            if not quiet:
                print "%s working directory of %s run in %s" % (verb.title(), adjective, work_dir)
            if not preserve:
                rm_tree(work_dir)
    # Return the exit code of the command, but return a failing exit
    # code if the command succeeded but the post-command copying process
    # failed.
    if retval or success:
        return retval
    else:
        return 1

# Entry point
def plac_call_main():
    return plac.call(main)

if __name__ == "__main__":
    sys.exit(plac_call_main())

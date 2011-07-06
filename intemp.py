#!/usr/bin/env python

import plac
import tempfile
import os
import os.path
import sys
import subprocess
from shutil import copy2 as copy_file, move as move_file, copytree as copy_tree, rmtree as rm_tree

def ensure_nonexistent(dst, filenames, delete=False):
    """Ensure that each file does not exist in destination dir.

    If delete is False, then any files found to exist will raise an
    IOError. If delete is True, then any files found will be deleted."""
    for f in filenames:
        destfile = os.path.join(dst, f)
        if os.path.lexists(destfile):
            if delete:
                if os.path.isdir(destfile):
                    shutil.rmtree(destfile)
                else:
                    os.unlink(destfile)
            else:
                raise IOError("Destination file %s already exists in %s" % (f, dst))

def do_sync(src, dst, overwrite=False, move=False):
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
            print "Move %s to %s" % (f, dst)
            move_file(srcfile, dstfile)
        elif os.path.isdir(srcfile):
            print "Copy dir %s to %s" % (f, dst)
            copy_tree(srcfile, dstfile, symlinks=True)
        else:
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

# Entry point
def plac_call_main():
    return plac.call(main)

@plac.annotations(
    # arg=(helptext, kind, abbrev, type, choices, metavar)
    command=("The command to execute. This is best specified last after all options and a double dash: --", "positional"),
    temp_dir=("The command will be run in an empty subdirectory of this directory. After completion, all files (and directories) produced in the the subdirectory will be moved to the target directory.", "option", "t", directory),
    target_dir=("The directory where output files will be moved after the program exits successfully. By default, this is the current working directory.", "option", "d", directory, None, "DIR"),
    preserve_temp_dir=("When to preserve the temporary directory after completion. By default, the temporary directory is preserved only if the command fails.", "option", "p", str, ("always", "never", "failure"), 'always|never|failure'),
    overwrite=("Overwrite files in destination directory.", "flag", "o"),
    )
def main(temp_dir=tempfile.gettempdir(), target_dir=os.getcwd(), overwrite=False,
         preserve_temp_dir="failure", *command):
    """Run a command in a temporary directory.

    If the command succeeds, then the contents of the temporary
    directory will be moved to the target directory (default pwd). If
    the command fails, the files will remain in the temporary
    directory (which may or may not be deleted, depending on options).

    IMPORTANT: Since the specified program is run in a temporary
    directory, all paths to input files should be given as absolute
    paths, not relative ones. On the other hand, specifying relative
    paths for output files is recommended, since this will produce the
    output files in the temporary directory."""
    work_dir = None
    success = False
    try:
        work_dir = tempfile.mkdtemp(dir=temp_dir)
        print "Running in %s" % work_dir
        print "Command: %s" % subprocess.list2cmdline(command)
        retval = subprocess.call(command, cwd=work_dir)
        success = retval == 0

        if success:
            print "Command was successful"
            try:
                do_sync(src=work_dir, dst=target_dir, overwrite=overwrite, move=preserve_temp_dir != 'always')
            except IOError:
                success = False
                print "Failed to copy result files to target dir"
        else:
            print "Command failed"
    finally:
        if not work_dir:
            pass
        elif not os.path.isdir(work_dir):
            pass
        else:
            if success:
                preserve = preserve_temp_dir == 'always'
            else:
                preserve = preserve_temp_dir != 'never'
            verb = "preserving" if preserve else "deleting"
            adjective = "successful" if success else "failed"
            print "%s working directory of %s run in %s" % (verb.title(), adjective, work_dir)
            if not preserve:
                rm_tree(work_dir)

if __name__ == "__main__":
    plac_call_main()

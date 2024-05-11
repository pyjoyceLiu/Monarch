# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT

import pdb
import common as c
import copy
import os
import fault_model
from utils import zero_terminiated_str,check_W_perm,check_R_perm
from checker import _print_hex

# ERROR CODE
ERR_ARG = 0x01
ERR_OBJ = 0x02
ERR_MIS = 0x03

# STAT CODE
IN_MD = 1 # in both memory and disk
IN_M  = 2 # in memory
IN_D  = 3 # in disk
IN_NE = 4 # not existent


def emulate(prev_state, call_idx):

    # Deep copy state from previous state
    state = copy.deepcopy(prev_state)

    # Set state as global
    c.BUF_DATA = state["BUF_DATA"]
    c.BUF_SIZE = state["BUF_SIZE"]
    c.FD_STACK = state["FD_STACK"]
    c.DENTRY = state["DENTRY"]
    c.MEM = state["MEM"]
    c.DISK = state["DISK"]
    c.UNSYNCED = state["UNSYNCED"]
    c.INODE_CNT = state["INODE_CNT"]
    c.cnt_recursion = state["CNT_RECUR"]
    c.FT = state["FT"]
    c.NODESTATE = state["NODESTATE"]
    c.CURNODE = c.runtime_state[call_idx]["ProcId"]

    # Get syscall info
    syscall_info = c.SYSCALL_STACK[call_idx]
    syscall = syscall_info[0]
    argv = syscall_info[1]
    syscall_ret = syscall_info[2]

    print("{} {} {}".format(" "*(4*c.ident), syscall, argv))

    ret = 0

    # Execute fault syscalls whenenver
    if syscall == "SYS_syz_failure_down":
        if c.FSTYPE not in ["nfs", "glusterfs", "cephfs"]:
            exit()
        ret = syz_failure_down(argv, c.CURNODE)
        return ret, state
    elif syscall == "SYS_syz_failure_up":
        if c.FSTYPE not in ["nfs", "glusterfs", "cephfs"]:
            exit()
        ret = syz_failure_up(argv, c.CURNODE)
        return ret, state
    elif syscall == "SYS_syz_failure_net_down":
        if c.FSTYPE not in ["nfs", "glusterfs", "cephfs"]:
            exit()
        ret = syz_failure_net_down(argv, c.CURNODE)
        return ret, state
    elif syscall == "SYS_syz_failure_net_up":
        if c.FSTYPE not in ["nfs", "glusterfs", "cephfs"]:
            exit()
        ret = syz_failure_net_up(argv, c.CURNODE)
        return ret, state
    '''
    elif syscall == "SYS_syz_failure_crash_client":
        ret = syz_failure_crash_client(argv, call_idx)
    elif syscall == "SYS_syz_failure_crash_server":
        ret = syz_failure_crash_server(argv, call_idx)
    '''

    # If FS syscalls, apply the fault model
    # Continue the emulation
    # only if the operation can be executed in current fault situation
    if fault_model.is_available(syscall, argv) == False:
        print("not available, skip")
        return -1, state

    if syscall == "SYS_mkdir":
        ret = mkdir(argv)
    elif syscall == "SYS_rmdir":
        ret = rmdir(argv)
    elif syscall == "SYS_rename":
        ret = rename(argv)
    elif syscall == "SYS_truncate":
        ret = truncate(argv) #
    elif syscall == "SYS_ftruncate":
        ret = ftruncate(argv) #
    elif syscall == "SYS_link":
        ret = link(argv)
    elif syscall == "SYS_symlink":
        ret = symlink(argv)
    elif syscall == "SYS_unlink":
        ret = unlink(argv)
    elif syscall == "SYS_fsync":
        ret = fsync(argv)
    elif syscall == "SYS_sync":
        ret = sync()
    elif syscall == "SYS_fdatasync":
        ret = fdatasync(argv)
    elif syscall == "SYS_syncfs":
        ret = syncfs(argv)
    elif syscall == "SYS_open":
        ret = open(argv, syscall_ret) #
    elif syscall == "SYS_write":
        ret = write(argv) #
    elif syscall == "SYS_pwrite64":
        ret = pwrite64(argv) #
    elif syscall == "SYS_read":
        ret = read(argv) #
    elif syscall == "SYS_pread64":
        ret = pread64(argv) #
    elif syscall == "SYS_lseek":
        ret = lseek(argv) #
    elif syscall == "SYS_fallocate":
        ret = fallocate(argv) #
    elif syscall == "SYS_utimes":
        ret = utimes(argv)
    elif syscall == "SYS_readlink":
        ret = readlink(argv) #
    elif syscall == "SYS_chmod":
        ret = chmod(argv) #
    elif syscall == "SYS_fchmod":
        ret = fchmod(argv)
    elif syscall == "SYS_setxattr":
        ret = setxattr(argv) #
    elif syscall == "SYS_lsetxattr":
        ret = lsetxattr(argv)
    elif syscall == "SYS_fsetxattr":
        ret = fsetxattr(argv)
    elif syscall == "SYS_removexattr":
        ret = removexattr(argv)
    elif syscall == "SYS_lremovexattr":
        ret = lremovexattr(argv)
    elif syscall == "SYS_fremovexattr":
        ret = fremovexattr(argv)
    elif syscall == "SYS_listxattr":
        ret = listxattr(argv)
    elif syscall == "SYS_llistxattr":
        ret = llistxattr(argv)
    elif syscall == "SYS_flistxattr":
        ret = flistxattr(argv)
    elif syscall == "SYS_close":
        ret = close(argv)
    elif syscall == "SYS_getxattr":
        ret = getxattr(argv)
    elif syscall == "SYS_lgetxattr":
        ret = lgetxattr(argv)
    elif syscall == "SYS_fgetxattr":
        ret = fgetxattr(argv)
    elif syscall == "SYS_dup":
        ret = dup(argv, syscall_ret)
    elif syscall == "SYS_dup2":
        ret = dup2(argv, syscall_ret)
    elif syscall == "SYS_getdents":
        ret = getdents(argv)
    elif syscall == "SYS_stat":
        ret = stat(argv)
    elif syscall == "SYS_lstat":
        ret = lstat(argv)
    elif syscall == "SYS_fstat":
        ret = fstat(argv)

    # Write global state back to the local state
    state["INODE_CNT"] = c.INODE_CNT
    state["CNT_RECUR"] = c.cnt_recursion
    # Others like NODESTATE, MEM, DISK, they are sharing the same obj
    print("syscall returns:", ret)
    return ret, state

def _print_err(code, funcname, argc, argv):
    if c.verbose:
        if code == ERR_ARG:
            print "[-] EMUL-ERR {0} requires at least {1} args, {2} given".format(
                    funcname, argc, len(argv))
        elif code == ERR_OBJ:
            print "[-] EMUL-ERR Wrong object detected in {0}({1})".format(funcname, argv)
        elif code == ERR_MIS:
            print "[-] EMUL-ERR Missing inode detedted in {0}({1})".format(funcname, argv)


def _abspath(pathstr):
    if pathstr == "" or pathstr == None:
        return None
    elif not pathstr.startswith("./") and pathstr != ".":
        return os.path.join(".", pathstr)
    else:
        return pathstr


def _get_path(string): # gets file path from variable name
    """
    Gets path that a variable holds, convert it to start from root (.),
    esolves any symbolic link and returns the converted path.
    """
    varname = string.replace("(long)", "")
    try:
        path = c.BUF_DATA[varname]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR {0} is not a variable holding path".format(varname)
        return None

    try:
        size = c.BUF_SIZE[varname]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR the path size of {0} does not exist".format(varname)
        return None
    # mkdir(&(0x7f0000000380)='\x00', 0x4)
    if size <= 0 or (size == 1 and path == '\x00'):
        if c.verbose:
            print "[-] EMUL-ERR the path pointed by {0} is empty".format(varname)
        return None
    print("debug path", path, size, size <= 0)
    path = _res_path(path)
    return _abspath(path)


def _get_raw_path(string): # gets file path from variable name
    """
    Gets the exact path string that a variable holds as is.
    """
    varname = string.replace("(long)", "")
    try:
        path = c.BUF_DATA[varname]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR {0} is not a variable holding path".format(varname)
        return None

    try:
        size = c.BUF_SIZE[varname]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR the path size of {0} does not exist".format(varname)
        return None

    if size <= 0:
        if c.verbose:
            print "[-] EMUL-ERR the path pointed by {0} is empty".format(varname)
        return None

    return path


def _get_raw_path_from_state(string, state): # gets file path from variable name
    """
    Gets the exact path string that a variable holds as is.
    """
    varname = string.replace("(long)", "")
    try:
        path = state["BUF_DATA"][varname]
    except KeyError:
        if c.verbose:
            print "[-] DEP-CHECK {0} is not a variable holding path".format(varname)
        return ""

    try:
        size = c.BUF_SIZE[varname]
    except KeyError:
        if c.verbose:
            print "[-] DEP-CHECK the path size of {0} does not exist".format(varname)
        return ""

    if size <= 0:
        if c.verbose:
            print "[-] DEP-CHECK the path pointed by {0} is empty".format(varname)
        return "" 

    return path

def _res_path(pathstr):
    pathstr = _abspath(pathstr)
    namelist = pathstr.split("/")
    flag = 0
    for i in xrange(1, len(namelist)+1):
        subpath = '/'.join(namelist[:i])
        try:
            subid = c.DENTRY[subpath]
            try:
                subinode = c.MEM[subid]
            except KeyError:
                subinode = c.DISK[subid]

            if subinode.type == c.SYMLINK:
                target = subinode.target
                namelist[i-1] = target
                flag = 1
            else:
                pass
        except KeyError:
            pass
    if flag:
        newpathstr = "/".join(namelist)
        pathstr = os.path.normpath(newpathstr)
        c.cnt_recursion += 1
        if c.cnt_recursion > c.MAX_SYMLINK:
            c.cnt_recursion = 0
            if c.verbose:
                print "[-] EMUL-ERR too many levels of symbolic links"
            return _abspath(pathstr)
        return _res_path(pathstr)
    else:
        if c.verbose:
            "(path resolved: {0})".format(_abspath(pathstr))
        c.cnt_recursion = 0
        return _abspath(pathstr)


def _get_inode_of_fd_from_state(fd_var, state):
    
    varname = fd_var.replace("(long)", "")
    try:
        inode = state["FD_STACK"][varname]
    except KeyError:
        if c.verbose:
            print "[-] DEP-CHECK {} not a valid file descriptor".format(varname)
        return "", ""
    if inode == "":
        if c.verbose:
            print "[-] DEP-CHECK fd {0} is not defined".format(varname)
        return "", ""

    return varname, inode.path

def _get_inode_of_fd(string): # gets inode object from fd variable name
    """
    if succeed, returns inode object
    else, returns -1 (only for fsync)
    """
    print "fd name: {}".format(string)
    varname = string.replace("(long)", "")
    inode = None
    try:
        inode = c.FD_STACK[varname]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR {} not a valid file descriptor".format(varname)
            print c.FD_STACK
        return -1
    if inode == "":
        if c.verbose:
            print "[-] EMUL-ERR fd {0} is not defined".format(varname)
        return -1

    # Get the inode ID from the FD_STACK
    # And then read the inode from the mem or disk

    try:
        inode = c.MEM[inode.id]
    except:
        inode = c.DISK[inode.id]

    return inode

def _reset_inode_of_fd(string):

    varname = string.replace("(long)", "")
    try:
        inode = c.FD_STACK[varname]
        c.FD_STACK[varname] = -1
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR {} not a valid file descriptor".format(varname)
            print c.FD_STACK
        return -1

def _get_size_and_data_of_buf(string): # gets the size and data of buffer
    varname = string.replace("(long)", "")
    return (int(c.BUF_SIZE[varname]), c.BUF_DATA[varname])


def _get_parent_path(path):
    if path == ".":
        return "."
    else:
        return "/".join(path.split("/")[:-1])


def _get_name(path):
    return path.split("/")[-1]


def _get_assigned_value_of_var(string):
    varname = string.replace("(long)", "")
    try:
        value = c.BUF_DATA[varname]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR Not a valid variable {0}".format(varname)
        return -1
    return value


def _exist(path):
    try:
        id = c.DENTRY[path]
        return 1
    except KeyError:
        return 0


def _chk_stat(id):
    if id in c.DISK and id in c.MEM:
        # print id, "in both disk and memory"
        # not persisted after previous ops
        # apply ops on MEM
        return IN_MD
    elif id in c.MEM and id not in c.DISK:
        # print id, "only in MEM"
        # probably a new file or dir
        # apply ops on MEM
        return IN_M
    elif id not in c.MEM and id in c.DISK:
        # print id, "only in DISK"
        # should copy object from DISK to MEM
        # apply ops on MEM
        return IN_D
    else:
        # print id, "non-existent"
        # possible if it's a new object
        # otherwise error
        return IN_NE


def _get_parent_inode(id_parent):
    try: # parent inode must exist either in MEM or DISK
        inode_parent = c.MEM[id_parent]
    except KeyError:
        try:
            inode_parent = c.DISK[id_parent]
        except KeyError:
            inode_parent = None
    if inode_parent is None: # if not, must be an error
        if c.verbose:
            print "[-] EMUL-ERR parent inode doesn't exist"
        return -1

    return inode_parent


def _add_child_to_parent_dentry(tup, inode_parent):
    """
    1. Add current tuple(id, name) to parent inode's children list
    2. Unsync parent inode
        2-1. Add (or override) parent inode in MEM
        2-2. Remove (if exists) parent inode from DISK
    """
    inode_parent.add_child(tup)
    id_parent = inode_parent.id
    c.MEM[id_parent] = inode_parent
    if id_parent in c.DISK:
        c.DISK.pop(id_parent, None)


def _remove_child_from_parent_dentry(tup, inode_parent, unlink=0):
    """
    Move tuple from inode_parent.children list to d_children list.
    Can only be called by rename, unlink, and rmdir (destructive ops).
    """
    inode_parent.remove_child(tup, unlink)
    id_parent = inode_parent.id
    c.MEM[id_parent] = inode_parent
    if id_parent in c.DISK:
        c.DISK.pop(id_parent, None)


def _unsync_inode_by_id(id):
    ret = _chk_stat(id)
    if ret == IN_D: # existing inode is in disk
        inode = c.DISK[id]
        inode_mem = copy.deepcopy(inode)
        c.MEM[inode_mem.id] = inode_mem
        c.DISK.pop(id, None)
    elif ret == IN_NE:
        _print_err(ERR_OBJ, __name__, None, argv)
        return 1


def _update_dentry():
    tuplist = c.FT.nodes
    for path in c.DENTRY.keys():
        name = _get_name(path)
        parent_path = _get_parent_path(path)
        parent_name = _get_name(parent_path)

        id = c.DENTRY[path]
        tup = (id, name)

        id_parent = c.DENTRY[parent_path]
        tup_parent = (id_parent, parent_name)

        _, path_str = c.FT.get_path(start=c.ROOT, goal=tup, goaldir=tup_parent)
        if path != path_str:
            c.DENTRY.pop(path, None)
            c.DENTRY[path_str] = id


def _resolve_symlink_path(path, inode, all_paths):
    """
    resolves the path pointed to by symlink recursively, and returns the final
    inode object
    """
    res_path = os.path.join(_get_parent_path(path), inode.target)
    res_path = os.path.normpath(res_path)
    res_path = _abspath(res_path)

    all_paths.append(inode.target)

    try:
        res_id = c.DENTRY[res_path]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR Symlink's resolved path {0} does not exist".format(
                    res_path)
        c.cnt_recursion = 0
        return -1, -1

    try:
        inode = c.MEM[res_id]
    except KeyError:
        inode = c.DISK[res_id]

    if inode.type == c.SYMLINK:
        c.cnt_recursion += 1
        if c.cnt_recursion > c.MAX_SYMLINK:
            c.cnt_recursion = 0
            if c.verbose:
                print "[-] EMUL-ERR too many levels of symbolic links"
            return -1, -1
        return _resolve_symlink_path(res_path, inode, all_paths)
    else:
        if c.verbose:
            print "(symlink resolved: {0})".format(res_path)
        c.cnt_recursion = 0
        return res_path, inode


def _parse_open_flags(flags_as_int):

    # Just exit if there are flags we cannot handle
    black_list = {"O_PATH":010000000}
    for key in black_list:
        flag = black_list[key]
        if flag & flags_as_int != 0:
            if c.verbose:
                print("We cannot handle flag {} until now".format(key))
            exit()

    flags = oct(flags_as_int)
    str_flags = str(flags).replace("L", "")
    opt_dict = {}
    digitlist = [int(d) for d in str_flags.zfill(7)]

    bds = str(bin(digitlist[-7]))[2:].zfill(3)
    opt_dict[c.O_SYNC] = int(bds[0])
    opt_dict[c.O_CLOEXEC] = int(bds[1])
    opt_dict[c.O_NOATIME] = int(bds[2])

    bds = str(bin(digitlist[-6]))[2:].zfill(3)
    opt_dict[c.O_NOFOLLOW]= int(bds[0])
    opt_dict[c.O_DIRECTORY] = int(bds[1])
    opt_dict[c.O_LARGEFILE] = int(bds[2])

    bds = str(bin(digitlist[-5]))[2:].zfill(3)
    opt_dict[c.O_DIRECT] = int(bds[0])
    opt_dict[c.FASYNC] = int(bds[1])
    opt_dict[c.O_DSYNC] = int(bds[2])

    bds = str(bin(digitlist[-4]))[2:].zfill(3)
    opt_dict[c.O_NONBLOCK] = int(bds[0])
    opt_dict[c.O_APPEND] = int(bds[1])
    opt_dict[c.O_TRUNC] = int(bds[2])

    bds = str(bin(digitlist[-3]))[2:].zfill(3)
    opt_dict[c.O_NOCTTY] = int(bds[0])
    opt_dict[c.O_EXCL] = int(bds[1])
    opt_dict[c.O_CREAT] = int(bds[2])

    bds = str(bin(digitlist[-1]))[2:].zfill(2)
    if bds == "11":
        opt_dict[c.O_ACCMODE] = 1
        opt_dict[c.O_RDWR] = 0
        opt_dict[c.O_WRONLY] = 0
        opt_dict[c.O_RDONLY] = 0
    else:
        opt_dict[c.O_ACCMODE] = 0
        opt_dict[c.O_RDWR] = int(bds[0])
        opt_dict[c.O_WRONLY] = int(bds[1])
        opt_dict[c.O_RDONLY] = 0
        if not int(bds[0]):
            if not int(bds[1]):
                opt_dict[c.O_RDONLY] = 1

    return opt_dict


def open(argv, varname):
    """
    int open(const char *path, int oflag, ... );
    It shall create an open file description that refers to a file
    and a file descriptor that refers to that open file description.
    Values for oflag shall specify exactly one of the three below:
    - O_RDONLY (0 in JANUS)
    - O_WRONLY (1 in JANUS)
    - O_RDWR   (2 in JANUS)
    """
    _update_dentry()
    path = _get_path(argv[0])
    if path == None:
        if c.verbose:
            print "[-] EMUL-ERR path not exist"
        return 1
    name = _get_name(path)
    parent_path = _get_parent_path(path)
    parent_name = _get_name(parent_path)
    try:
        id_parent = c.DENTRY[parent_path]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR path {0} not valid".format(path)
        return 1

    flags = int(argv[1])
    #if flags > 1048576:
    #    if c.verbose:
    #        print "[-] EMUL-ERR invalid flag: {0}".format(flags)
    #    return 1

    opt_dict = _parse_open_flags(flags)
    tup_parent = (id_parent, parent_name)
    inode_parent = _get_parent_inode(id_parent)
    if inode_parent == -1:
        return 1
    if inode_parent.type == c.SYMLINK:
        _, inode_parent = _resolve_symlink_path(parent_path, inode_parent, [])
        if inode_parent == -1:
            return 1

    if inode_parent.type != c.DIR:
        if c.verbose:
            print "[-] EMUL-ERR {0} is not a directory".format(parent_path)
        return 1

    try: # file to open already exists in image
        id_fd = c.DENTRY[path]
        try:
            inode = c.MEM[id_fd]
        except KeyError:
            inode = c.DISK[id_fd]

        if opt_dict[c.O_CREAT] and opt_dict[c.O_EXCL]:
            if c.verbose:
                print "[-] EMUL-ERR cannot open existing files with O_CREAT | O_EXCL"
            return 1

        if opt_dict[c.O_DIRECTORY] and inode.type != c.DIR:
            if c.verbose:
                print "[-] EMUL-ERR cannot open non-directory {0} with O_DIRECTORY flag".format(path)
            return 1

        if inode.type == c.DIR and (opt_dict[c.O_WRONLY] or opt_dict[c.O_RDWR]):
            if c.verbose:
                print "[-] EMUL-ERR cannot open directory with O_WRONLY or O_RDWR"
            return 1

        if opt_dict[c.O_NOFOLLOW] and inode.type == c.SYMLINK:
            if c.verbose:
                print "[-] EMUL-ERR cannot open symlink with O_NOFOLLOW flag"
            return 1

        if inode.type == c.SYMLINK:
            _, inode = _resolve_symlink_path(path, inode, [])
            if inode == -1:
                return 1
            id = inode.id
        else:
            id = id_fd

        if id in c.DISK:
            # unsync from DISK because access time changes
            inode_mem = copy.deepcopy(c.DISK[id])
            c.DISK.pop(id, None)
            c.MEM[inode_mem.id] = inode_mem
        else:
            # leave if inode is in MEM
            inode_mem = c.MEM[id]

        if opt_dict[c.O_TRUNC] and (opt_dict[c.O_RDWR] or opt_dict[c.O_WRONLY]):
            if inode_mem.type == c.FILE:
                inode_mem.size = 0

        inode_mem.opt_dict[varname] = opt_dict

    except KeyError: # new path - create file
        if not opt_dict[c.O_CREAT]:
            if c.verbose:
                print "[-] EMUL-ERR cannot create file {0} without O_CREAT flag".format(path)
            return 1

        if opt_dict[c.O_DIRECTORY]:
            if c.verbose:
                print "[-] EMUL-ERR non-specified behavior for O_CREAT | O_DIRECTORY"
            exit()

        if argv[2]:
            mode = int(argv[2]) & c.MODEMASK & ~c.UMASK
        else:
            mode = 0644
        print "mode", mode

        id_fd = c.INODE_CNT

        inode_mem = c.Inode(id=id_fd, name=name, type=c.FILE, mode=mode, size=0, path=path)
        #if c.FSTYPE == c.NFS:
        #    inode_mem.xattr["system.nfs4_acl"] = ""
        c.MEM[inode_mem.id] = inode_mem
        c.DENTRY[path] = inode_mem.id
        tup = (id_fd, name)
        c.FT.add_node(tup, tup_parent)
        inode_mem.opt_dict[varname] = opt_dict

        _add_child_to_parent_dentry(tup, inode_parent)

    c.FD_STACK[varname] = inode_mem
    inode_mem.offset[varname] = 0 # init offset for fd
    inode_mem.refs += 1

    if c.verbose:
        print "[+] opened {0} (inode #{1}) and saved in {2}".format(path, inode_mem.id, varname)
        #print "options:", opt_dict
        #print "stat mode", inode_mem.mode


def mkdir(argv):
    """
    int mkdir(const char *path, mode_t mode)
    - The mkdir() function shall create a new directory with name path.
    - The newly created directory shall be an empty directory.
    - If path names a symbolic link, mkdir() shall fail and set errno to [EEXIST].
    """
    if len(argv) == 1:
        argv.append(0755) # assumption: default permission is 755
    if len(argv) < 2:
        _print_err(ERR_ARG, __name__, 2, argv)
        return 1
    _update_dentry()

    path = _get_path(argv[0])
    if path == None:
        if c.verbose:
            print "[-] EMUL-ERR path not exist"
        return 1
    name = _get_name(path)
    parent_path = _get_parent_path(path)
    parent_name = _get_name(parent_path)
    mode = int(argv[1]) & c.MODEMASK & ~c.UMASK

    # 1. check for existence of path
    try:
        id = c.DENTRY[path]
    except KeyError:
        id = c.INODE_CNT

    try:
        id_parent = c.DENTRY[parent_path]
    except KeyError: # if parent doesn't exist in the tree, it's an error
        if c.verbose:
            print "[-] EMUL-ERR cannot recursively mkdir (parent inode doesn't exist)"
        return 1

    inode_parent = _get_parent_inode(id_parent)
    if inode_parent == -1:
        return 1
    if inode_parent.type == c.SYMLINK:
        parent_path, inode_parent = _resolve_symlink_path(parent_path, inode_parent, [])
        if inode_parent == -1:
            return 1
        id_parent = inode_parent.id
        parent_name = _get_name(parent_path)

    if inode_parent.type != c.DIR:
        if c.verbose:
            print "[-] EMUL-ERR {0} is not a directory".format(parent_path)
        return 1

    ret = _chk_stat(id)
    if ret == IN_NE: # mkdir only when path doesn't exist
        inode = c.Inode(id=id, name=name, type=c.DIR, mode=mode, size=4096, linkcnt=2, path=path)
        #if c.FSTYPE == c.NFS:
        #    inode.xattr["system.nfs4_acl"] = ""
        tup = (id, name)
        tup_parent = (id_parent, parent_name)
        c.FT.add_node(tup, tup_parent)
        c.MEM[inode.id] = inode
        c.DENTRY[path] = inode.id

        _add_child_to_parent_dentry(tup, inode_parent)

        if c.verbose:
            print "[+] Made directory {0}".format(path)


def rmdir(argv):
    """
    The rmdir() function shall remove a directory whose name is given by path.
    The directory shall be removed only if it is an empty directory.
    """
    if len(argv) < 1:
        _print_err(ERR_ARG, __name__, 1, argv)
        return 1
    _update_dentry()

    path = _get_path(argv[0])
    if path == None:
        if c.verbose:
            print "[-] EMUL-ERR path not exist"
        return 1
    name = _get_name(path)

    parent_path = _get_parent_path(path)
    parent_name = _get_name(parent_path)

    try:
        id = c.DENTRY[path]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR path does not exist"
        return 1
    tup = (id, name)

    try:
        inode = c.MEM[id]
    except KeyError:
        inode = c.DISK[id]

    if inode.type != c.DIR:
        if c.verbose:
            print "[-] EMUL-ERR {0} is not a directory".format(path)
        return 1

    # 1. Get children nodes
    children = c.FT[tup][0].children
    if children:
        if c.verbose:
            print "[-] EMUL-ERR cannot remove non-empty directory {0}".format(path)
        return 1

    # 2. Get parent id
    try:
        id_parent = c.DENTRY[parent_path]
    except KeyError: # if parent doesn't exist in the tree, it's an error
        #_print_err(ERR_MIS, __name__, None, argv)
        if c.verbose:
            print "[-] EMUL-ERR parent node does not exist"
        return 1
    tup_parent = (id_parent, parent_name)

    inode_parent = _get_parent_inode(id_parent)
    if inode_parent == -1:
        return 1
    if inode_parent.type == c.SYMLINK:
        _, inode_parent = _resolve_symlink_path(parent_path, inode_parent, [])
        if inode_parent == -1:
            return 1

    ret = _chk_stat(id)
    if ret == IN_D: # copy to mem and remove name, also remove from DENTRY
        inode = c.DISK[id]
        if inode.type != c.DIR:
            if c.verbose:
                print "[-] EMUL-ERR cannot rmdir non-directory: {0} is type {1}".format(path, inode.type)
            return 1
        inode_mem = copy.deepcopy(inode)
        inode_mem.removed = 1
        c.DISK.pop(id, None)
        c.MEM[id] = inode_mem
    elif ret == IN_MD or ret == IN_M:
        inode = c.MEM[id]
        if inode.type != c.DIR:
            if c.verbose:
                print "[-] EMUL-ERR cannot rmdir non-directory: {0} is type {1}".format(path, inode.type)
            return 1
        inode.removed = 1

    inode.remove_name(name)
    _remove_child_from_parent_dentry(tup, inode_parent)

    if inode.refs == 0:
        c.FT.remove_node(tup, tup_parent)

    c.DENTRY.pop(path, None)
    if c.verbose:
        print "[+] Removed directory {0}".format(path)


def link(argv):
    """
    int link(const char *path1, const char *path2);
    - The link() function shall create a new link (directory entry)
      for the existing file, path1.
    - The path1 argument points to a pathname naming an existing file.
    - The path2 argument points to a pathname naming the
      new directory entry to be created.
    - If path1 names a directory, link() shall fail unless the process has
      appropriate privileges and the implementation supports using
      link() on directories.
    """
    if len(argv) < 2:
        _print_err(ERR_ARG, __name__, 2, argv)
        return 1
    _update_dentry()

    path_existing = _abspath(_get_raw_path(argv[0]))
    if path_existing == None:
        if c.verbose:
            print "[-] EMUL-ERR not path is specified"
        return 1
    name_existing = _get_name(path_existing)
    path_new = _get_raw_path(argv[1])
    if path_new == None:
        if c.verbose:
            print "[-] EMUL-ERR not path is specified"
        return 1
    path_existing_parent = _get_parent_path(path_existing)
    path_existing_parent = _res_path(path_existing_parent)
    name_existing_parent = _get_name(path_existing_parent)
    path_existing = _abspath(os.path.normpath(os.path.join(path_existing_parent, name_existing)))

    print "path_existing", path_existing, "path_new", path_new, argv[0], argv[1]

    try:
        id_existing_parent = c.DENTRY[path_existing_parent]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR parent inode of path1 doesn't exist"
        return 1

    if path_existing == ".":
        if c.verbose:
            print "[-] EMUL-ERR cannot create link to '.'"
        return 1

    try:
        id_existing = c.DENTRY[path_existing]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR path 1 ({0}) does not exist".format(
                    path_existing)
        return 1
    try:
        inode = c.DISK[id_existing]
    except KeyError:
        inode = c.MEM[id_existing]
    if inode.type == c.DIR:
        if c.verbose:
            print "[-] EMUL-ERR hard link not allowed for directory"
        return 1
    if path_new in c.DENTRY:
        if c.verbose:
            print "[-] EMUL-ERR path2 already exists"
        return 1
    path_new_parent = _get_parent_path(path_new)
    try:
        id_new_parent = c.DENTRY[path_new_parent]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR invalid path2"
        return 1

    name_new_parent = _get_name(path_new_parent)
    tup_new_parent = (id_new_parent, name_new_parent)
    name_existing = _get_name(path_existing)
    tup_existing = (id_existing, name_existing)
    name_new = _get_name(path_new)
    tup_new = (id_existing, name_new)

    inode_new_parent = _get_parent_inode(id_new_parent)
    if inode_new_parent == -1:
        return 1
    if inode_new_parent.type == c.SYMLINK:
        _, inode_new_parent = _resolve_symlink_path(path_new_parent, inode_new_parent, [])
        if inode_new_parent == -1:
            return 1

    if inode_new_parent.type != c.DIR:
        if c.verbose:
            print "[-] EMUL-ERR {0} is not a directory".format(path_new_parent)
        return 1

    c.FT.add_node(tup_new, tup_new_parent)
    _add_child_to_parent_dentry(tup_new, inode_new_parent)

    ret_existing = _chk_stat(id_existing)
    if ret_existing == IN_D: # existing inode is in disk
        # increment link_cnt of existing inode by 1
        # unsync it
        inode_existing = c.DISK[id_existing]
        inode_existing_mem = copy.deepcopy(inode_existing)
        inode_existing_mem.add_hardlink(name_new)
        c.MEM[id_existing] = inode_existing_mem

        # when link is created to inode in disk, we should regard the node
        # as being unsynced, because linkcnt (invariant) is changing!
        c.DISK.pop(id_existing, None)

    elif ret_existing == IN_M or ret_existing == IN_MD:
        inode_existing = c.MEM[id_existing]
        inode_existing.add_hardlink(name_new)

    elif ret_existing == IN_NE:
        _print_err(ERR_MIS, __name__, None, argv)
        return 1

    c.DENTRY[path_new] = id_existing
    if c.verbose:
        print "[+] Linked new name {0} to {1}".format(path_new, path_existing)


def unlink(argv):
    """
    int unlink(const char *path);
    The unlink() function shall remove a link to a file.
    - If path names a symbolic link, unlink() shall remove the symbolic link
      named by path and shall not affect any file or directory named by
      the contents of the symbolic link.
    - Otherwise, unlink() shall remove the link named by the pathname
      pointed to by path and shall decrement the link count of the file
      referenced by the link.
    - The path argument shall not name a directory.
    - If the name referred to a symbolic link, the link is removed. (not target)
    """
    # unlink(dir) -> fail, unlink(file) -> removes it.
    if len(argv) < 1:
        _print_err(ERR_ARG, __name__, 1, argv)
        return 1
    _update_dentry()

    path = _abspath(_get_raw_path(argv[0]))
    if path == None:
        if c.verbose:
            print "[-] EMUL-ERR not path is specified"
        return 1
    name = _get_name(path)
    path_parent = _get_parent_path(path)
    path_parent = _res_path(path_parent)
    path = _abspath(os.path.normpath(os.path.join(path_parent, name)))
    name_parent = _get_name(path_parent)
    try:
        id_parent = c.DENTRY[path_parent]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR parent node does not exist"
        return 1

    try:
        id = c.DENTRY[path]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR path does not exist"
        return 1

    tup_parent = (id_parent, name_parent)
    inode_parent = _get_parent_inode(id_parent)
    if inode_parent == -1:
        return 1
    if inode_parent.type == c.SYMLINK:
        _, inode_parent = _resolve_symlink_path(path_parent, inode_parent, [])
        if inode_parent == -1:
            return 1

    ret = _chk_stat(id)

    try:
        inode = c.DISK[id]
    except KeyError:
        inode = c.MEM[id]

    if inode.type == c.DIR:
        if c.verbose:
            print "[-] EMUL-ERR cannot unlink a directory {0}".format(path)
        return 1

    _unsync_inode_by_id(id)
    inode = c.MEM[id]
    inode.remove_name(name)
    inode.linkcnt -= 1

    tup = (id, name)

    if inode.refs == 0:    
        c.FT.remove_node(tup, tup_parent)

    _remove_child_from_parent_dentry(tup, inode_parent, unlink=1)
    c.DENTRY.pop(path, None)

    if c.verbose:
        print "[+] Unlinked {0}, refs={1}".format(path, inode.refs)

def close(argv):
    if len(argv) < 1:
        _print_err(ERR_ARG, __name__, 1, argv)
        return -1
    fd = argv[0]
    varname = fd.replace("(long)", "")

    inode = _get_inode_of_fd(fd)
    if inode == -1:
        return -1

    inode.refs -= 1
    if inode.refs == 0:
        _reset_inode_of_fd(fd)

    return 0

def symlink(argv):
    """
    int symlink(const char *path1, const char *path2);
    The symlink() function shall create a symbolic link called path2
    that contains the string pointed to by path1.
    """
    if len(argv) < 2:
        _print_err(ERR_ARG, __name__, 2, argv)
        return 1
    _update_dentry()

    path1 = _get_raw_path(argv[0]) # original file path
    #path1 is NULL
    if path1 == None:
        if c.verbose:
            print "[-] EMUL-ERR invalid original file path (e.g., NULL)"
        return 1
    path1_name = _get_name(path1)

    path2 = _get_raw_path(argv[1]) # symlink
    if path2 == None:
        if c.verbose:
            print "[-] EMUL-ERR not path is specified"
        return 1
    path2_name = _get_name(path2)
    path2_parent_path = _get_parent_path(path2)
    path2_parent_name = _get_name(path2_parent_path)
    try:
        id_parent = c.DENTRY[path2_parent_path]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR invalid path"
        return 1
    tup_parent = (id_parent, path2_parent_name)
    inode_parent = _get_parent_inode(id_parent)
    if inode_parent == -1:
        return 1
    if inode_parent.type == c.SYMLINK:
        _, inode_parent = _resolve_symlink_path(path2_parent_name, inode_parent, [])
        if inode_parent == -1:
            return 1

    if path2 in c.DENTRY:
        if c.verbose:
            print "[-] EMUL-ERR cannot create symlink with existing path {0}".format(path2)
        return 1
    if inode_parent.type != c.DIR:
        if c.verbose:
            print "[-] EMUL-ERR {0} is not a directory".format(path2_parent_path)
        return 1

    id = c.INODE_CNT
    inode_mem = c.Inode(id=c.INODE_CNT, name=path2_name, type=c.SYMLINK, mode=0777, size=0, path=path2)
    #if c.FSTYPE == c.NFS:
    #    inode_mem.xattr["system.nfs4_acl"] = ""
    inode_mem.target = path1
    inode_mem.size = len(path1)
    c.MEM[inode_mem.id] = inode_mem
    c.DENTRY[path2] = inode_mem.id
    tup = (id, path2_name)
    _add_child_to_parent_dentry(tup, inode_parent)
    c.FT.add_node(tup, tup_parent)

    if c.verbose:
        print "[+] created symlink {0} pointing to {1}".format(path2, path1)
        print "attr:", inode_mem.xattr

def rename(argv):
    """
    int rename(const char* oldpath, const char *newpath);
    The rename() function shall change the name of a file.
    If the old argument points to the pathname of a file that is not a directory,
    the new argument shall not point to the pathname of a directory.
    If the link named by the new argument exists, it shall be removed and old renamed to new.
    If new names an existing directory, it shall be required to be an empty directory.
    - If oldpath refers to a symbolic link, the link is renamed.
      (the target is not affected.)
    - If newpath refers to a symbolic link, the link will be overwritten.
      (the target is not affected.)
    """
    if len(argv) < 2:
        _print_err(ERR_ARG, __name__, 2, argv)
        return 1
    _update_dentry()

    path_old = _abspath(_get_raw_path(argv[0]))
    if path_old == None:
        if c.verbose:
            print "[-] EMUL-ERR not path is specified"
        return 1
    name_old = _get_name(path_old)

    path_new = _abspath(_get_raw_path(argv[1]))
    if path_new == None:
        if c.verbose:
            print "[-] EMUL-ERR not path is specified"
        return 1
    name_new = _get_name(path_new)

    path_old_parent = _get_parent_path(path_old)
    path_old_parent = _res_path(path_old_parent)
    path_old = _abspath(os.path.normpath(os.path.join(path_old_parent, name_old)))
    name_old_parent = _get_name(path_old_parent)

    path_new_parent = _get_parent_path(path_new)
    path_new_parent = _res_path(path_new_parent)
    path_new = _abspath(os.path.normpath(os.path.join(path_new_parent, name_new)))
    name_new_parent = _get_name(path_new_parent)

    if path_old == path_new:
        if c.verbose:
            print "[-] EMUL-ERR cannot rename to same file"
        return 1

    if path_old == ".":
        if c.verbose:
            print "[-] EMUL-ERR cannot rename '.'"
        return 1

    try:
        id_old = c.DENTRY[path_old]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR old path does not exist"
        return 1

    # Get old's parent id
    try:
        id_parent_old = c.DENTRY[path_old_parent]
    except KeyError: # if parent doesn't exist in the tree, it's an error
        #_print_err(ERR_MIS, __name__, None, argv)
        if c.verbose:
            print "[-] EMUL-ERR parent node does not exist"
        return 1
    # Get new's parent id
    try:
        id_parent_new = c.DENTRY[path_new_parent]
    except KeyError: # if parent doesn't exist in the tree, it's an error
        #_print_err(ERR_MIS, __name__, None, argv)
        if c.verbose:
            print "[-] EMUL-ERR parent node does not exist"
        return 1

    inode_old_parent = _get_parent_inode(id_parent_old)
    if inode_old_parent == -1:
        return 1
    if inode_old_parent.type == c.SYMLINK:
        path_old_parent, inode_old_parent = _resolve_symlink_path(path_old_parent, inode_old_parent, [])
        if inode_old_parent == -1:
            return 1
        name_old_parent = _get_name(path_old_parent)
        try:
            id_parent_old = c.DENTRY[path_old_parent]
        except KeyError:
            if c.verbose:
                print "[-] EMUL-ERR old parent's path {0} does not exist".format(
                        path_old_parent)
            return 1

    inode_new_parent = _get_parent_inode(id_parent_new)
    if inode_new_parent == -1:
        return 1
    if inode_new_parent.type == c.SYMLINK:
        path_new_parent, inode_new_parent = _resolve_symlink_path(path_new_parent, inode_new_parent, [])
        if inode_new_parent == -1:
            return 1
        name_new_parent = _get_name(path_new_parent)
        try:
            id_parent_new = c.DENTRY[path_new_parent]
        except KeyError:
            if c.verbose:
                print "[-] EMUL-ERR new parent's path {0} does not exist".format(
                        path_new_parent)
            return 1

    if inode_new_parent.type != c.DIR:
        if c.verbose:
            print "[-] EMUL-ERR {0} is not a directory".format(path_new_parent)
        return 1

    tup_old_parent = (id_parent_old, name_old_parent)
    tup_new_parent = (id_parent_new, name_new_parent)

    tup_old = (id_old, name_old)

    path_tup_list, pathstr = c.FT.get_path(c.ROOT, tup_new_parent, c.ROOT)
    if tup_old in path_tup_list:
        if c.verbose:
            print "[-] EMUL-ERR cannot rename {0} to its subdirectory, {1}".format(
                    path_old, path_new)
        return 1

    try:
        inode_old = c.MEM[id_old]
    except KeyError:
        inode_old = c.DISK[id_old]

    """
    if inode_old.type == c.SYMLINK:
        inode_old = _resolve_symlink_path(path_old, inode_old)
        if inode_old == -1:
            return 1
        id_old = inode_old.id
    """

    inode_new_existing = None
    if _exist(path_new): # if new path exists, we have to check type mismatch
        id_new = c.DENTRY[path_new]
        try:
            inode_new_existing = c.MEM[id_new]
        except KeyError:
            inode_new_existing = c.DISK[id_new]

        tup_new_existing = (id_new, name_new)
        new_children = None
        if len(c.FT[tup_new_existing]) == 1: # meaning that it is a directory
            new_children = c.FT[tup_new_existing][0].children
        if new_children:
            if c.verbose:
                print "[-] EMUL-ERR new path is not empty (has children)"
            return 1

        if (inode_old.type == c.DIR and inode_new_existing.type != c.DIR)\
                or\
            (inode_old.type != c.DIR and inode_new_existing.type == c.DIR):
            if c.verbose:
                print "[-] EMUL-ERR rename type mismatch"
            return 1

        if inode_old.id == inode_new_existing.id:
            if c.verbose:
                print "[-] EMUL-ERR {0} and {1} are the same files".format(
                        path_old, path_new)
            return 1
    # Handling old file: keep inode, change name from old to new
    # then, remove the old name from name-id-map

    # if new path exists
    if inode_new_existing:
        if inode_old.type == c.FILE: # rename fail situation 1 - rename FILE to DIR
            if inode_new_existing.type == c.DIR:
                if c.verbose:
                    print "[-] EMUL-ERR cannot rename file {0} to directory {1}".format(path_old, path_new)
                return 1
        elif inode_old.type == c.DIR: # rename fail situation 2 - rename DIR to non DIR
            if inode_new_existing.type != c.DIR:
                if c.verbose:
                    print "[-] EMUL-ERR cannot rename directory {0} to non-directory {1}".format(path_old, path_new)
                return 1
    # new path does not exist

    # Even though name is changed, no not unsync
    if name_old != name_new:
        inode_old.remove_name(name_old, name_new)
        inode_old.add_name(name_new)

    tup_old = (id_old, name_old)
    tup_new = (id_old, name_new) # map old id to new name
    c.FT.modify_node(tup_old, tup_new, tup_old_parent, tup_new_parent)

    # if the new path already existed
    if inode_new_existing:
        c.FT.remove_node(tup_new_existing, tup_new_parent)
        inode_new_existing.linkcnt -= 1
        _unsync_inode_by_id(id_new)
        _remove_child_from_parent_dentry(tup_new_existing, inode_new_parent)

    _remove_child_from_parent_dentry(tup_old, inode_old_parent)
    _add_child_to_parent_dentry(tup_new, inode_new_parent)
    c.DENTRY.pop(path_old, None)
    c.DENTRY[path_new] = id_old
    child_dentry_list = []
    for path in c.DENTRY:
        if path.startswith(path_old):
            child_dentry_list.append((path, c.DENTRY[path]))
    for child_dentry in child_dentry_list:
        child_path = child_dentry[0]
        child_inum = child_dentry[1]
        c.DENTRY.pop(child_path, None)
        c.DENTRY[child_path.replace(path_old, path_new)] = child_inum

    if c.verbose:
        print "[+] Renamed {0} to {1}".format(path_old, path_new)

def sync():
    """
    The sync() function shall cause all information in memory that updates
    file systems to be scheduled for writing out to all file systems.
    """
    keys = list(c.MEM.keys())
    for id_mem in c.MEM:
        c.DISK[id_mem] = copy.deepcopy(c.MEM[id_mem])
        if c.DISK[id_mem].type == c.FILE:
            c.DISK[id_mem].datablock.synced = 1
    for id_mem in keys:
        c.MEM.pop(id_mem, None)

    # remove the dirent history of directories
    for inum in c.DISK:
        inode = c.DISK[inum]
        if inode.type == c.DIR:
            inode.persist_children()

    if c.verbose:
        print "[+] synced {0} inodes".format(len(keys))

def syncfs(argv):
    """
    This is not POSIX standard, but JANUS supports this instead of sync.
    We'll use this API as a wrapper for sync, doing:
    - check if the given argument (file descriptor) is valid
    - if valid, call sync().
    """
    if len(argv) < 1:
        _print_err(ERR_ARG, __name__, 1, argv)
        return 1

    inode = _get_inode_of_fd(argv[0])
    if inode == -1:
        return 1
    else:
        sync()

def fsync(argv):
    """
    The fsync() function shall request that all data for the
    open file descriptor named by fildes is to be transferred
    to the storage device associated with the file described by fildes.
    As well as flushing the file data, fsync() also flushes the metadata
    information associated with the file
    Calling fsync() does not necessarily ensure that the entry in the
    directory containing the file has also reached disk. For that an
    explicit fsync() on a file descriptor for the directory is also
    needed.
    """
    if len(argv) < 1:
        _print_err(ERR_ARG, __name__, 1, argv)
        return 1

    inode = _get_inode_of_fd(argv[0])
    if inode == -1:
        if c.verbose:
            print "EMUL-ERR inode not found"
        return 1

    if inode.id in c.MEM:
        inode_mem = c.MEM[inode.id]
        c.DISK[inode.id] = copy.deepcopy(inode_mem)
        if c.DISK[inode.id].type == c.FILE:
            c.DISK[inode.id].datablock.synced = 1
        c.MEM.pop(inode.id, None)

        if c.verbose:
            print "[+] fsynced inode #{0}: {1}".format(inode.id, argv[0])
    else:
        if c.verbose:
            print "[+] inode #{0}: {1} is already fsync'ed".format(
                    inode.id, argv[0])

    # at this point, this inode is in disk
    inode_disk = c.DISK[inode.id]
    if inode_disk.type == c.DIR:
        # if directory, persist children's names
        inode_disk.persist_children()
    '''
    else:
        # XXX: Temporarily allowed fsync(path) for testing purpose!!
        path = _get_path(argv[0])
        if path == 1:
            if c.verbose:
                print "[-] aborting fsync"
            return 1
        name = _get_name(path)
        _update_dentry()
        id = c.DENTRY[path]

        ret = _chk_stat(id)
        if ret == IN_D: # existing inode is in disk
            # fsyncing something already in disk is pointless,
            # but its data could have been changed and unsynced.
            if c.DISK[id].type == c.FILE:
                c.DISK[id].datablock.synced = 1
        elif ret == IN_M or ret == IN_MD:
            inode_mem = c.MEM[id]
            c.DISK[id] = copy.deepcopy(inode_mem)
            if c.DISK[id].type == c.FILE:
                c.DISK[id].datablock.synced = 1
            c.MEM.pop(inode_mem.id, None)
        if c.verbose:
            print "[+] fsynced {0}".format(argv[0])
    '''

def fdatasync(argv):
    """
    int fdatasync(int fildes);
    - The fdatasync() function shall force all currently queued I/O operations
      associated with the file indicated by file descriptor fildes to the
      synchronized I/O completion state.
    - The functionality shall be equivalent to fsync() with the symbol
      _POSIX_SYNCHRONIZED_IO defined, with the exception that all I/O
      operations shall be completed as defined for synchronized I/O data
      integrity completion.
    """
    if len(argv) < 1:
        _print_err(ERR_ARG, __name__, 1, argv)
        return 1

    fd = argv[0]
    inode = _get_inode_of_fd(fd)
    if inode == -1:
        return 1
    id = inode.id
    try:
        inode = c.MEM[inode.id]
    except:
        inode = c.DISK[inode.id]

    if inode.type == c.FILE:
        inode.datablock.synced = 1

    if c.verbose:
        print "[+] fdatasynced {0}".format(argv[0])

def fallocate(argv):
    """
    int posix_fallocate(int fd, off_t offset, off_t len);
    - The posix_fallocate() function shall ensure that any required storage
      for regular file data starting at offset and continuing for len bytes
      is allocated on the file system storage media.
    - If the offset+ len is beyond the current file size, then
      posix_fallocate() shall adjust the file size to offset+ len.
      Otherwise, the file size shall not be changed.

    # IMPORTANT
    Implemented in the syscall mutator is not posix_fallocate.
    It's a Linux-specific system call described below:
    int fallocate(int fd, int mode, off_t offset, off_t len);
    - fallocate() allows the caller to directly manipulate the allocated
      disk space for the file referred to by fd for the byte range starting
      at offset and continuing for len bytes.
    - The  mode  argument  determines the operation to be performed on the
      given range.

    * https://github.com/torvalds/linux/blob/master/include/uapi/linux/falloc.h
    FALLOC_FL_KEEP_SIZE = 0x01
    FALLOC_FL_PUNCH_HOLE = 0x02
    FALLOC_FL_NO_HIDE_STALE = 0X04
    FALLOC_FL_COLLAPSE_RANGE = 0X08
    FALLOC_FL_ZERO_RANGE = 0X10
    FALLOC_FL_INSERT_RANGE = 0X20
    FALLOC_FL_UNSHARE_RANGE = 0X40
    """

    if len(argv) < 4:
        _print_err(ERR_ARG, __name__, 3, argv)
        return 1
    fd = argv[0]

    inode = _get_inode_of_fd(fd)
    if inode == -1:
        return 1
    id = inode.id
    try:
        inode = c.MEM[inode.id]
    except:
        inode = c.DISK[inode.id]

    if inode.type != c.FILE:
        if c.verbose:
            print "[-] EMUL-ERR cannot fallocate to non-regular file {0}".format(
                    str(inode.name))
        return 1

    if inode.opt_dict[fd][c.O_ACCMODE]:
        if c.verbose:
            print "[-] EMUL-ERR Cannot perform under O_ACCMODE"
        return 1

    if inode.opt_dict[fd][c.O_RDONLY]:
        if c.verbose:
            print "[-] EMUL-ERR cannot write to file (O_RDONLY is set)"
        return 1

    mode = int(argv[1])
    if mode == 0:
        default = 1
    else:
        default = 0
    mode = bin(mode)[2:]
    mode = mode[::-1]
    mode_vec = [0, 0, 0, 0, 0, 0, 0]
    for idx, digit in enumerate(mode):
        mode_vec[idx] = int(digit)

    keep_size = mode_vec[0]
    punch_hole = mode_vec[1]
    no_hide_stale = mode_vec[2]
    collapse_range = mode_vec[3]
    zero_range = mode_vec[4]
    insert_range = mode_vec[5]
    unshare_range = mode_vec[6]

    offset = int(argv[2])
    length = int(argv[3])
    if (offset < 0) or (length <= 0):
        if c.verbose:
            print "[-] error in offset or length"
        return 1

    if default: # POSIX
        if offset + length > inode.size:
            old_size = inode.size
            new_size = offset + length
            inode.size = new_size

            pad_len = offset + length - old_size
            inode.datablock.data += "\x00" * pad_len
            """
            front = inode.datablock.hole[:old_size]
            newhole = "\x00" * (new_size - old_size)
            rear = inode.datablock.hole[new_size:]
            inode.datablock.hole = front + newhole + rear
            """

            _unsync_inode_by_id(inode.id)
            inode = c.MEM[inode.id]
            inode.datablock.synced = 0

    # Below: POSIX extension
    # first check for mode errors
    error = 0
    if collapse_range and (offset + length) > inode.size:
        error = 1
    if insert_range and offset > inode.size:
        error = 1
    if (collapse_range or insert_range) and \
       (keep_size or punch_hole or no_hide_stale or zero_range or unshare_range):
        error = 1
    if (collapse_range or zero_range or insert_range) and (inode.type != c.FILE):
        error = 1
    if (collapse_range or insert_range) and \
       (offset % 1024 != 0) and (length % 1024 != 0):
        error = 1
    if punch_hole and not keep_size:
        error = 1
    """
    if not default and \
        (collapse_range or zero_range or insert_range or punch_hole) == 0:
        error = 1
    """

    if error:
        if c.verbose:
            print "[-] EMUL-ERR mode error"
        return 1

    # then emulate if extension option's set
    if keep_size and not (punch_hole or collapse_range or insert_range):
        if offset + length > inode.size:
            dummysize = offset + length
            bs = dummysize / c.BLKSIZE
            if dummysize % c.BLKSIZE:
                bs += 1
            inode.numblk = bs * c.BLKSIZE / 512

        zero_range = 0
    if zero_range or punch_hole:
        if offset + length > inode.size:
            if keep_size:
                if offset > inode.size:
                    # has no effect if offset starts from beyond size
                    pass
                else:
                    new_data = inode.datablock.data[:offset]\
                             + "\x00" * (inode.size - offset)
                    inode.datablock.data = new_data
                    if punch_hole:
                        front = inode.datablock.hole[:offset]
                        newhole = "\x00" * (length)
                        rear = inode.datablock.hole[offset+length:]
                        inode.datablock.hole = front + newhole + rear
                    inode.datablock.synced = 0
                    _unsync_inode_by_id(inode.id)
            else: # keep_size is not set
                if offset > inode.size:
                    new_size = offset + length - inode.size
                    new_data = inode.datablock.data \
                             + "\x00" * new_size
                else:
                    new_size = offset + length
                    new_data = inode.datablock.data[:offset] \
                             + "\x00" * length
                inode.size = new_size
                inode.datablock.data = new_data
                if punch_hole:
                    front = inode.datablock.hole[:offset]
                    newhole = "\x00" * (length)
                    rear = inode.datablock.hole[offset+length:]
                    inode.datablock.hole = front + newhole + rear
                inode.datablock.synced = 0
                _unsync_inode_by_id(inode.id)
        else:
            new_data = inode.datablock.data[:offset] \
                     + "\x00" * length \
                     + inode.datablock.data[offset+length:]
            inode.datablock.data = new_data
            if punch_hole:
                front = inode.datablock.hole[:offset]
                newhole = "\x00" * (length)
                rear = inode.datablock.hole[offset+length:]
                inode.datablock.hole = front + newhole + rear
            inode.datablock.synced = 0
            _unsync_inode_by_id(inode.id)
    elif collapse_range:
        new_data = inode.datablock.data[:offset] \
                 + inode.datablock.data[offset+length:]
        new_size = inode.size - length
        inode.size = new_size
        inode.datablock.data = new_data

        front = inode.datablock.hole[:offset]
        newhole_filled = "\xff" * (length)
        rear = inode.datablock.hole[offset+length:]
        inode.datablock.hole = front + newhole_filled + rear

        inode.datablock.synced = 0
        _unsync_inode_by_id(inode.id)
    elif insert_range:
        new_data = inode.datablock.data[:offset] \
                 + "\x00" * length \
                 + inode.datablock.data[offset:]
        new_size = inode.size + length
        inode.size = new_size
        inode.datablock.data = new_data

        front = inode.datablock.hole[:offset]
        newhole = "\xff" * (length)
        rear = inode.datablock.hole[offset+length:]
        inode.datablock.hole = front + newhole + rear
        inode.datablock.synced = 0
        _unsync_inode_by_id(inode.id)

    if c.verbose:
        print "[+] fallocated to {0}".format(inode.name)

def read(argv):
    """
    ssize_t read(int fildes, void *buf, size_t nbyte);
    - The read() function shall attempt to read nbyte bytes from the file
      associated with the open file descriptor, fildes, into the buffer
      pointed to by buf.
    """
    if len(argv) < 3:
        _print_err(ERR_ARG, __name__, 3, argv)
        return 1
    fd = argv[0]
    varname = fd.replace("(long)", "")

    inode = _get_inode_of_fd(fd)
    if inode == -1:
        return -1
    id = inode.id
    try:
        inode = c.MEM[inode.id]
    except:
        inode = c.DISK[inode.id]

    if not check_R_perm(inode.mode):
        if c.verbose:
            print "[-] not have the read permission {}".format(oct(inode.mode))
        return -1

    if inode.opt_dict[varname][c.O_ACCMODE]:
        if c.verbose:
            print "[-] EMUL-ERR Cannot perform under O_ACCMODE"
        return -1

    if inode.opt_dict[varname][c.O_WRONLY]:
        if c.verbose:
            print "[-] EMUL-ERR cannot read from file (O_WRONLY is set)"
        return -1

    if inode.type != c.FILE:
        if c.verbose:
            print "[-] EMUL-ERR {0} is not a regular file".format(inode.name)
        return -1

    buf_var = argv[1].replace("(long)", "")
    try:
        buf_size = int(c.BUF_SIZE[buf_var])
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR buffer variable {0} is not initialized".format(buf_var)
        return -1
    try:
        buf_data = c.BUF_DATA[buf_var]
    except KeyError:
        buf_data = ""
        return -1

    cur_offset = inode.offset[varname]
    inode_size = inode.size
    nbyte = int(argv[2])

    if cur_offset >= inode_size:
        nbyte = 0

    else:
        if nbyte > inode_size - cur_offset:
            nbyte = inode_size - cur_offset

        if buf_size < nbyte:
            # if the size of buffer is not large enough to hold nbyte bytes,
            # as much as buf_size will be written to the buffer.
            # However, buffer overflow happens, and other buffers are affected..
            nbyte = buf_size

        buf_data = inode.datablock.data[cur_offset:cur_offset+nbyte]
        c.BUF_DATA[buf_var] = buf_data

        inode.offset[varname] += nbyte
        # the inode offset is reinitialized to 0 when fd is closed then reopened
        # or by lseek(fd, 0, SEEK_CUR);

    if c.verbose:
        print "[+] Read {0} bytes from {1} to buffer {2}".format(
                nbyte, inode.name, buf_var)
    return nbyte

def pread64(argv):
    """
    ssize_t pread(int fildes, void *buf, size_t nbyte, off_t offset);
    - The pread() function shall be equivalent to read(), except that it shall
      read from a given position in the file without changing the file offset.
    - The first three arguments to pread() are the same as read() with the
      addition of a fourth argument offset for the desired position inside
      the file.
    """
    if len(argv) < 4:
        _print_err(ERR_ARG, __name__, 3, argv)
        return -1
    fd = argv[0]

    inode = _get_inode_of_fd(fd)
    if inode == -1:
        return -1
    try:
        inode = c.MEM[inode.id]
    except:
        inode = c.DISK[inode.id]

    if not check_R_perm(inode.mode):
        if c.verbose:
            print "[-] not have the read permission {}".format(oct(inode.mode))
        return -1

    if inode.opt_dict[fd][c.O_ACCMODE]:
        if c.verbose:
            print "[-] EMUL-ERR Cannot perform under O_ACCMODE"
        return -1

    if inode.opt_dict[fd][c.O_WRONLY]:
        if c.verbose:
            print "[-] EMUL-ERR cannot read from file (O_WRONLY is set)"
        return -1

    if inode.type != c.FILE:
        if c.verbose:
            print "[-] EMUL-ERR {0} is not a regular file".format(inode.name)
        return -1

    buf_var = argv[1].replace("(long)", "")
    try:
        buf_size = int(c.BUF_SIZE[buf_var])
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR buffer variable {0} is not initialized".format(buf_var)
        return -1
    try:
        buf_data = c.BUF_DATA[buf_var]
    except KeyError:
        buf_data = ""
        return -1

    offset = int(argv[3])
    inode_size = inode.size
    nbyte = int(argv[2])

    if offset > inode_size:
        nbyte = 0

    else:
        if nbyte > inode_size - offset:
            nbyte = inode_size - offset

        if buf_size < nbyte:
            # if the size of buffer is not large enough to hold nbyte bytes,
            # as much as buf_size will be written to the buffer.
            # However, buffer overflow happens, and other buffers are affected..
            nbyte = buf_size

        buf_data = inode.datablock.data[offset:offset+nbyte]
        c.BUF_DATA[buf_var] = buf_data

    if c.verbose:
        print "[+] Pread {0} bytes from offset {1} of {2} to buf {3}".format(
                nbyte, offset, inode.name, buf_var)

    return nbyte

def write(argv):
    """
    ssize_t write(int fildes, const void *buf, size_t nbyte);
    - The write() function shall attempt to write nbyte bytes from the buffer
      pointed to by buf to the file associated with the open file descriptor,
      fildes.
    - nbyte is zero and the file is a regular file, the write() function
      may detect and return errors
    - On a file not capable of seeking, writing shall always take place
      starting at the current position.
    """
    if len(argv) < 3:
        _print_err(ERR_ARG, __name__, 3, argv)
        return 1
    fd = argv[0]
    varname = fd.replace("(long)", "")

    inode = _get_inode_of_fd(fd)
    if inode == -1:
        return 1
    id = inode.id
    try:
        inode = c.MEM[inode.id]
    except:
        inode = c.DISK[inode.id]

    if not check_W_perm(inode.mode):
        if c.verbose:
            print "[-] not have the write permission {}".format(oct(inode.mode))
        return 1

    if inode.type != c.FILE:
        if c.verbose:
            print "[-] Cannot write to non-regular file {0} {1}".format(
                    varname, str(inode.name))
        return 1

    if inode.opt_dict[varname][c.O_ACCMODE]:
        if c.verbose:
            print "[-] EMUL-ERR Cannot perform under O_ACCMODE"
        return 1

    if inode.opt_dict[varname][c.O_RDONLY]:
        if c.verbose:
            print "[-] EMUL-ERR cannot write to file (O_RDONLY is set)"
        return 1

    buf_var = argv[1].replace("(long)", "")
    try:
        buf_size = int(c.BUF_SIZE[buf_var])
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR buffer variable {0} is not initialized: {}".format(
                    buf_var, c.BUF_SIZE)
        return 1
    try:
        buf_data = c.BUF_DATA[buf_var]
    except KeyError:
        buf_data = ""
        pass

    if inode.opt_dict[varname][c.O_APPEND]:
        cur_offset = inode.size
    else:
        cur_offset = inode.offset[varname]

    nbyte = int(argv[2])
    if nbyte == 0:
        if c.verbose:
            print "[+] Wrote {0} bytes from buffer {1} to {2}".format(
                    nbyte, buf_var, inode.name)
        return 0

    if nbyte > buf_size:
        # when nbyte is larger than the size of buffer,
        # the contents of buffer will be first written to the file (beginning
        # from the current offset) then whatever garbage existing after the
        # buffer will also be written to the file.
        garbage = "\x00" * (nbyte - buf_size)
    else:
        garbage = ""

    existing_data_before_offset = inode.datablock.data[:cur_offset]
    if len(inode.datablock.data) < cur_offset:
        # add null-padding if current offset is beyond the data
        padding = "\x00" * (cur_offset - len(inode.datablock.data))
        existing_data_after_offset_and_nbyte = ""
    else:
        padding = ""
        existing_data_after_offset_and_nbyte = inode.datablock.data[cur_offset+nbyte:]

    new_data = existing_data_before_offset \
             + padding \
             + buf_data[:nbyte] \
             + garbage \
             + existing_data_after_offset_and_nbyte
    inode.datablock.data = new_data
    inode.datablock.synced = 0

    front = inode.datablock.hole[:cur_offset]
    newhole_filled = "\xff"*nbyte
    rear = inode.datablock.hole[cur_offset+nbyte:]
    inode.datablock.hole = front + newhole_filled + rear

    inode.size = len(new_data)
    inode.numblk = inode.size / 512
    if inode.size > inode.numblk * 512:
        inode.numblk += 1
    inode.offset[varname] += nbyte

    _unsync_inode_by_id(inode.id)

    if c.verbose:
        print "[+] Wrote {0} bytes from buffer {1} to {2}".format(
                nbyte, buf_var, inode.name)

def pwrite64(argv):
    """
    ssize_t write(int fildes, const void *buf, size_t nbyte, off_t offset);
    - The pwrite() function shall be equivalent to write(), except that it
      writes into a given position and does not change the file offset
      (regardless of whether O_APPEND is set).
    - The first three arguments to pwrite() are the same as write() with
      the addition of a fourth argument offset for the desired position inside
      the file. An attempt to perform a pwrite() on a file that is incapable
      of seeking shall result in an error.
    """
    if len(argv) < 4:
        _print_err(ERR_ARG, __name__, 3, argv)
        return 1
    fd = argv[0]
    varname = fd.replace("(long)", "")

    inode = _get_inode_of_fd(fd)
    if inode == -1:
        return 1
    id = inode.id
    try:
        inode = c.MEM[inode.id]
    except:
        inode = c.DISK[inode.id]

    if not check_W_perm(inode.mode):
        if c.verbose:
            print "[-] not have the write permission {}".format(oct(inode.mode))
        return 1

    if inode.type != c.FILE:
        if c.verbose:
            print "[-] Cannot write to non-regular file {0} {1}".format(
                    varname, str(inode.name))
        return 1

    if inode.opt_dict[varname][c.O_ACCMODE]:
        if c.verbose:
            print "[-] EMUL-ERR Cannot perform under O_ACCMODE"
        return 1

    if inode.opt_dict[varname][c.O_RDONLY]:
        if c.verbose:
            print "[-] EMUL-ERR cannot write to file (O_RDONLY is set)"
        return 1

    buf_var = argv[1].replace("(long)", "")
    try:
        buf_size = int(c.BUF_SIZE[buf_var])
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR buffer variable {0} is not initialized".format(
                    buf_var)
        return 1
    try:
        buf_data = c.BUF_DATA[buf_var]
    except KeyError:
        buf_data = ""
        pass

    offset = int(argv[3])

    nbyte = int(argv[2])
    if nbyte == 0:
        if c.verbose:
            print "[+] Pwrote {0} bytes from buffer {1} to offset {2} of file {3}"\
                    .format(nbyte, buf_var, offset, inode.name)
        return 0

    if nbyte > buf_size:
        # when nbyte is larger than the size of buffer,
        # the contents of buffer will be first written to the file (beginning
        # from the current offset) then whatever garbage existing after the
        # buffer will also be written to the file.
        garbage = "\x00" * (nbyte - buf_size)
    else:
        garbage = ""

    existing_data_before_offset = inode.datablock.data[:offset]
    if len(inode.datablock.data) < offset:
        # add null-padding if offset is beyond the data
        padding = "\x00" * (offset - len(inode.datablock.data))
        existing_data_after_offset_and_nbyte = ""
    else:
        padding = ""
        existing_data_after_offset_and_nbyte = inode.datablock.data[offset+nbyte:]


    new_data = existing_data_before_offset \
             + padding \
             + buf_data[:nbyte] \
             + garbage \
             + existing_data_after_offset_and_nbyte
    inode.datablock.data = new_data
    inode.datablock.synced = 0

    front = inode.datablock.hole[:offset]
    newhole_filled = "\xff"*nbyte
    rear = inode.datablock.hole[offset+nbyte:]
    inode.datablock.hole = front + newhole_filled + rear

    inode.size = len(new_data)

    _unsync_inode_by_id(inode.id)

    if c.verbose:
        print "[+] Pwrote {0} bytes from buffer {1} to offset {2} of file {3}"\
                .format(nbyte, buf_var, offset, inode.name)

def lseek(argv):
    """
    off_t lseek(int fildes, off_t offset, int whence);
    - The lseek() function shall set the file offset for the open file
      description associated with the file descriptor fildes, as follows:
      - if whence is SEEK_SET (0), the file offset shall be set to offset bytes
      - if whence is SEEK_CUR (1), the file offset shall be set to its
        current location plus offset
      - if whence is SEEK_END (2), the file offset shall be set to the size
        of the file plus offset.
    """
    """
    Non-standard extention (supported by btrfs ocfs xfs ext4 tmpfs nfs fuse)
    whence SEEK_DATA (3) and SEEK_HOLE (4)
    """
    SEEK_SET = 0
    SEEK_CUR = 1
    SEEK_END = 2
    SEEK_DATA = 3
    SEEK_HOLE = 4

    if len(argv) < 3:
        _print_err(ERR_ARG, __name__, 3, argv)
        return 1

    fd = argv[0]
    varname = fd.replace("(long)", "")

    inode = _get_inode_of_fd(fd)
    if inode == -1:
        return 1
    id = inode.id
    try:
        inode = c.MEM[inode.id]
    except:
        inode = c.DISK[inode.id]

    if inode.type != c.FILE:
        if c.verbose:
            print "[-] EMUL-ERR cannot lseek on non-regular file {0}: {1}".format(
                    varname, str(inode.name))

    old_offset = inode.offset[varname]
    offset = int(argv[1])
    whence = int(argv[2])
    if whence > SEEK_HOLE:
        if c.verbose:
            print "[-] EMUL-ERR invalid value for whence: {0}".format(whence)
        return 1

    if whence == SEEK_SET:
        inode.offset[varname] = offset
    elif whence == SEEK_CUR:
        inode.offset[varname] += offset
    elif whence == SEEK_END:
        inode.offset[varname] = inode.size + offset
    elif whence == SEEK_DATA:
        if inode.size <= offset:
            if c.verbose:
                print "[-] offset if beyond the end of file"
            return 1
        data_offset = offset
        try:
            byte = inode.datablock.data[offset]
        except Indexerror:
            byte = None
        if byte:
            inode.offset[varname] = data_offset
        else:
            flag = 0
            for byte in inode.datablock.hole[data_offset:]:
                if byte == "\xff":
                    flag = 1
                    break
                data_offset += 1
            if flag:
                inode.offset[varname] = data_offset
            else:
                if c.verbose:
                    print "[-] lseek SEEK_DATA failed to find any data"
                return 1
    elif whence == SEEK_HOLE:
        if inode.size <= offset:
            if c.verbose:
                print "[-] offset is beyond the end of file"
            return 1
        hole_offset = offset
        flag = 0
        for byte in inode.datablock.hole[hole_offset:]:
            if byte == "\x00":
                flag = 1
                break
            hole_offset += 1
        if flag:
            inode.offset[varname] = hole_offset
        else:
            inode.offset[varname] = inode.size

    if c.verbose:
        print "[+] Changed offset from {0} to {1}".format(
                old_offset, inode.offset[varname])

def truncate(argv):
    """
    int truncate(const char *path, off_t length);
    - The truncate() function shall cause the regular file named by path to
      have a size which shall be equal to length bytes.
    - If the file previously was larger than length, the extra data is
      discarded. If the file was previously shorter than length, its size is
      increased, and the extended area appears as if it were zero-filled.
    """
    if len(argv) < 2:
        _print_err(ERR_ARG, __name__, 2, argv)
        return 1
    _update_dentry()

    path = _get_path(argv[0])
    if path == None:
        if c.verbose:
            print "[-] EMUL-ERR path not exist"
        return 1
    length = int(argv[1])

    try:
        id = c.DENTRY[path]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR file {0} does not exist".format(path)
        return 1

    try:
        inode = c.MEM[id]
    except:
        inode = c.DISK[id]

    if inode.type == c.SYMLINK:
        _, inode = _resolve_symlink_path(path, inode, [])
        if inode == -1:
            return 1
        id = inode.id

    if not check_W_perm(inode.mode):
        if c.verbose:
            print "[-] not have the write permission {}".format(oct(inode.mode))
        return 1

    if inode.type != c.FILE:
        if c.verbose:
            print "[-] Cannot truncate non-regular file {0}".format(path)
        return 1

    _unsync_inode_by_id(id)

    inode = c.MEM[id]

    old_length = inode.size
    inode.size = length

    if len(inode.datablock.data) >= length: # discard extra data
        inode.datablock.data = inode.datablock.data[:length]
        front = inode.datablock.hole[:length]
        newhole = "\x00" * (old_length - length)
        rear = inode.datablock.hole[old_length:]
        inode.datablock.hole = front + newhole + rear
        inode.datablock.synced = 0
    else: # zero-fill extended area
        inode.datablock.data += "\x00" * (length - len(inode.datablock.data))
        front = inode.datablock.hole[:old_length]
        newhole = "\x00" * (length - old_length)
        rear = inode.datablock.hole[length:]
        inode.datablock.hole = front + newhole + rear
        inode.datablock.synced = 0

    if c.verbose:
        print "[+] Truncated {0} from {1} to {2} bytes".format(
                path, old_length, length)

def ftruncate(argv):
    """
    int ftruncate(int fildes, off_t length);
    """
    if len(argv) < 2:
        _print_err(ERR_ARG, __name__, 2, argv)
        return 1

    fd = argv[0]

    inode = _get_inode_of_fd(fd)
    if inode == -1:
        if c.verbose:
            print "[-] EMUL-ERR invalid file descriptor: {0}".format(fd)
        return 1
    id = inode.id
    try:
        inode = c.MEM[inode.id]
    except:
        inode = c.DISK[inode.id]

    if not check_W_perm(inode.mode):
        if c.verbose:
            print "[-] not have the write permission {}".format(oct(inode.mode))
        return 1

    if inode.type != c.FILE:
        if c.verbose:
            print "[-] EMUL-ERR Cannot truncate non-regular file {0}".format(
                    str(inode.name))
        return 1

    if inode.opt_dict[fd][c.O_ACCMODE]:
        if c.verbose:
            print "[-] EMUL-ERR Cannot perform under O_ACCMODE"
        return 1

    if inode.opt_dict[fd][c.O_RDONLY]:
        if c.verbose:
            print "[-] EMUL-ERR cannot modify file (O_RDONLY is set)"
        return 1

    length = int(argv[1])

    _unsync_inode_by_id(inode.id)

    inode = c.MEM[inode.id]

    old_length = inode.size
    inode.size = length

    if len(inode.datablock.data) >= length: # discard extra data
        inode.datablock.data = inode.datablock.data[:length]
        front = inode.datablock.hole[:length]
        newhole = "\x00" * (old_length - length)
        rear = inode.datablock.hole[old_length:]
        inode.datablock.hole = front + newhole + rear
        inode.datablock.synced = 0
    else: # zero-fill extended area
        inode.datablock.data += "\x00" * (length - len(inode.datablock.data))
        front = inode.datablock.hole[:old_length]
        newhole = "\x00" * (length - old_length)
        rear = inode.datablock.hole[length:]
        inode.datablock.hole = front + newhole + rear
        inode.datablock.synced = 0

    if c.verbose:
        print "[+] ftruncated inode {0} from {1} to {2} bytes".format(
            inode.id, old_length, length)

def utimes(argv):
    """
    The utime() function shall set the access and modification times of the
    file named by the path argument.

    * Although we are not considering ctime, mtime, and atime for crash
      consistency testing, I included this API in the emulator because
      it should unsync an inode upon successful completion.
    """

    if len(argv) < 2:
        _print_err(ERR_ARG, __name__, 3, argv)
        return 1
    _update_dentry()

    path = _get_path(argv[0])

    pass

def readlink(argv):
    """
    ssize_t readlink(const char *restrict path, char *restrict buf,
           size_t bufsize);
    - The readlink() function shall place the contents of the symbolic link
      referred to by path in the buffer buf which has size bufsize.
      If the number of bytes in the symbolic link is less than bufsize,
      the contents of the remainder of buf are unspecified. If the buf argument
      is not large enough to contain the link content, the first bufsize bytes
      shall be placed in buf.
    - Upon successful completion, readlink() shall mark for update the last
      data access timestamp of the symbolic link.
    """
    if len(argv) < 3:
        _print_err(ERR_ARG, __name__, 3, argv)
        return -1
    _update_dentry()

    path = _abspath(_get_raw_path(argv[0]))
    if path == None:
        if c.verbose:
            print "[-] EMUL-ERR not path is specified"
        return -1
    name = _get_name(path)
    path_parent = _get_parent_path(path)
    path_parent = _res_path(path_parent)
    path = _abspath(os.path.normpath(os.path.join(path_parent, name)))

    buf_var = argv[1].replace("(long)", "")
    try:
        buf_size = int(c.BUF_SIZE[buf_var])
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR buffer variable {0} is not initialized".format(
                    buf_var)
        return -1

    if buf_size == 0:
        if c.verbose:
            print "[-] EMUL-ERR buffer size is zero"
        return -1

    try:
        buf_data = c.BUF_DATA[buf_var]
    except KeyError:
        buf_data = ""
        return -1

    request_size = int(argv[2])

    try:
        id = c.DENTRY[path]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR file {0} does not exist".format(path)
        return -1

    try:
        inode = c.MEM[id]
    except KeyError:
        inode = c.DISK[id]

    if inode.type != c.SYMLINK:
        if c.verbose:
            print "[-] EMUL-ERR cannot readlink from non-symlink"
        return -1

    if not check_R_perm(inode.mode):
        if c.verbose:
            print "[-] not have the read permission {}".format(oct(inode.mode))
        return -1

    target = inode.target
    return_size = min(min(request_size, buf_size), len(target))
    if buf_size > return_size:
        buf_data = target[:return_size] + buf_data[return_size:]
    else:
        buf_data = target[:return_size]
    c.BUF_DATA[buf_var] = buf_data

    if c.verbose:
        print "[+] read link target of file {0} and wrote to buffer {1}".format(
                path, buf_var)

    return return_size

def chmod_base(argv, fd):

    if len(argv) < 2:
        _print_err(ERR_ARG, __name__, 2, argv)
        return 1
    _update_dentry()

    inode = None
    if fd == -1:
        path = _get_path(argv[0])
        if path == None:
            if c.verbose:
                print "[-] EMUL-ERR path not exist"
            return 1
        try:
            id = c.DENTRY[path]
        except KeyError:
            if c.verbose:
                print "[-] EMUL-ERR file {0} does not exist".format(path)
            return 1
        try:
            inode = c.MEM[id]
        except KeyError:
            inode = c.DISK[id]
    else:
        inode = _get_inode_of_fd(fd)
        if inode == -1:
            if c.verbose:
                print "[-] EMUL-ERR inode for fd {} doesn't exist".format(fd)
            return -1

    id = inode.id

    new_mode = int(argv[1])
    # fchmod(r0, 0xbe0888a1c86747ff) should succeed
    new_mode &= 07777
    # if new_mode < 0 or new_mode > 07777:
    #    if c.verbose:
    #        print "[-] EMUL-ERR invalid mode: {0}".format(new_mode)
    #    return 1

    if inode.type == c.SYMLINK:
        _, inode_res = _resolve_symlink_path(path, inode, [])
        if inode_res == -1:
            return 1
        res_id = inode_res.id

        inode_res.mode = new_mode
        _unsync_inode_by_id(res_id)
        inode = c.MEM[res_id]

    else:
        inode.mode = new_mode
        _unsync_inode_by_id(id)
        inode = c.MEM[id]

    if c.verbose:
        print "[+] Changed mode of {0} to {1}".format(inode.name, inode.mode)

def chmod(argv):
    return chmod_base(argv, -1)

def fchmod(argv):
    if len(argv) < 2:
        _print_err(ERR_ARG, __name__, 2, argv)
        return 1
    fd = argv[0]
    return chmod_base(argv, fd)

def setxattr_base(argv, syscall_name, fd):
    """
    int setxattr (const char *path, const char *name,
                    const void *value, size_t size, int flags);
    - setxattr sets the value of the extended attribute identified by name
      and associated with the given path in the filesystem. The size of the
      value must be specified.
    - An  extended attribute name is a simple NULL-terminated string. The name
      includes a namespace prefix - there may be several, disjoint namespaces
      associated with an individual inode. The value of an extended attribute
      is a chunk of arbitrary textual or binary data of specified length.
    - The flags parameter can be used to refine the semantics of the operation.
      XATTR_CREATE specifies a pure create, which fails if the named attribute
      exists already. XATTR_REPLACE specifies a pure replace operation, which
      fails if the named attribute does not already exist. By default
      (no flags), the extended attribute will be created if need be, or will
      simply replace the value if the attribute exists.
    """

    if len(argv) < 5:
        _print_err(ERR_ARG, __name__, 5, argv)
        return 1
    _update_dentry()

    path = ""
    if fd == -1:
        path = _get_path(argv[0])
        if path == None:
            if c.verbose:
                print "[-] EMUL-ERR not path is specified"
            return 1

    xattr_name = _get_assigned_value_of_var(argv[1])
    if xattr_name == -1:
        if c.verbose:
            print "[-] EMUL-ERR invalid xattr name {0}".format(argv[1])
        return 1
    xattr_name = zero_terminiated_str(xattr_name)
    xattr_value_size, xattr_value = _get_size_and_data_of_buf(argv[2])
    xattr_size = int(argv[3])
    if xattr_value_size == 0 and xattr_size != 0:
        if c.verbose:
            # lsetxattr$user('./file0\x00', "user.x", 0x0, 0x0, 0x0) should pass
            # setxattr("./file0", "user.+@*)!-)", NULL, 53, 0) should fail
            # lsetxattr$trusted_overlay_redirect(&(0x7f0000000040)='./file0\x00', &(0x7f0000000100), &(0x7f00000000c0)='\x00', 0x1, 0x1)
            print "[-] EMUL-ERR xattr value is NULL"
        return 1
    xattr_flags = int(argv[4]) & 0xffffffff


    inode = None
    if fd == -1:
        try:
            id = c.DENTRY[path]
        except KeyError:
            if c.verbose:
                print "[-] EMUL-ERR file {0} does not exist".format(path)
            return 1
        try:
            inode = c.MEM[id]
        except KeyError:
            inode = c.DISK[id]
    else:
        inode = _get_inode_of_fd(fd)
        if inode == -1:
            if c.verbose:
                print "[-] EMUL-ERR inode is not found for fd {}".format(fd)
            return -1
    
    id = inode.id

    splits = xattr_name.split(".")
    if len(splits) < 2:
        print "[-] EMUL-ERR setxattr the xattr name format is wrong, not namespace.attr"
        return 1

    namespace = splits[0]
    priv_namespace = ["system", "security", "trusted"]
    if namespace in priv_namespace:
        # NFS doesn't allowit, but glusterfs allows it
        if c.FSTYPE == 'nfs':
            if c.verbose:
                print "[-] EMUL-ERR setxattr namespace {0} is not permitted".format(priv_namespace)
            return 1
    elif namespace == "user":
        pass
    else:
        if c.verbose:
            print "[-] EMUL-ERR setxattr invalid namespace"
        return 1

    remaining = "".join(splits[1:])
    if remaining == "":
        if c.verbose:
            print "[-] EMUL-ERR setxattr with empty content after namespace, such as 'namespace.'"
        return 1

    if inode.type == c.SYMLINK and syscall_name != "lsetxattr":
        _, inode = _resolve_symlink_path(path, inode, [])
        if inode == -1:
            return 1
        id = inode.id

    if not check_W_perm(inode.mode):
        if c.verbose:
            print "[-] not have the write permission {}".format(oct(inode.mode))
        return 1

    # XATTR_CREATE : 0x1
    # XATTR_REPLACE: 0x2
    if xattr_flags == 0:
        pass
    elif xattr_flags == 1:
        if xattr_name in inode.xattr:
            if c.verbose:
                print "[-] EMUL-ERR Invalid mode: xattr {0} already exists".format(
                        xattr_name)
            return 1
    elif xattr_flags == 2:
        if xattr_name not in inode.xattr:
            if c.verbose:
                print "[-] EMUL-ERR Invalid mode: xattr {0} does not exist".format(
                        xattr_name)
            return 1
    else:
        if c.verbose:
            print "[-] EMUL-ERR Invalid flag, not in [0, 1, 2]"
        return 1

    """
    if "\x00" in xattr_value:
        xattr_value = xattr_value[:xattr_value.find("\x00")]
    """
    if len(xattr_value) < xattr_size:
        xattr_value = xattr_value+'\x00'*(xattr_size - len(xattr_value))
    elif len(xattr_value) > xattr_size:
        xattr_value = xattr_value[:xattr_size]
    inode.xattr[xattr_name] = xattr_value
    _unsync_inode_by_id(id)

    if c.verbose:
        print "[+] Set xattr {0} to file {1}".format(xattr_name, path)
        print "value ({0} bytes):".format(len(xattr_value))
        _print_hex(xattr_value)
        print "current xattr:", inode.xattr

def setxattr(argv):
    return setxattr_base(argv, "setxattr", -1)

def lsetxattr(argv):
    return setxattr_base(argv, "lsetxattr", -1)

def fsetxattr(argv):
    if len(argv) < 5:
        _print_err(ERR_ARG, __name__, 5, argv)
        return 1
    fd = argv[0]
    return setxattr_base(argv, "fsetxattr", fd)

def removexattr_base(argv, syscall_name, fd):
    """
    int removexattr(const char *path, const char *name);
    - removexattr() removes the extended attribute identified by name and
           associated with the given path in the filesystem.
    """

    if len(argv) < 2:
        _print_err(ERR_ARG, __name__, 2, argv)
        return 1
    _update_dentry()

    path = ""
    if fd == -1:
        path = _get_path(argv[0])
        if path == None:
            if c.verbose:
                print "[-] EMUL-ERR not path is specified"
            return 1
    
    xattr_name = _get_assigned_value_of_var(argv[1])
    if xattr_name == -1:
        if c.verbose:
            print "[-] EMUL-ERR invalid xattr name {0}".format(argv[1])
        return 1
    xattr_name = zero_terminiated_str(xattr_name)

    inode = None
    if fd == -1:
        try:
            id = c.DENTRY[path]
        except KeyError:
            if c.verbose:
                print "[-] EMUL-ERR file {0} does not exist".format(path)
            return 1
        try:
            inode = c.MEM[id]
        except KeyError:
            inode = c.DISK[id]
    else:
        inode = _get_inode_of_fd(fd)
        if inode == -1:
            if c.verbose:
                print "[-] EMUL-ERR inode is not found for fd {}".format(fd)
            return -1
    
    id = inode.id

    if inode.type == c.SYMLINK and syscall_name != "lremovexattr":
        _, inode = _resolve_symlink_path(path, inode, [])
        if inode == -1:
            return 1
        id = inode.id

    if not check_W_perm(inode.mode):
        if c.verbose:
            print "[-] not have the write permission {}".format(oct(inode.mode))
        return 1

    if xattr_name in inode.xattr:
        inode.xattr.pop(xattr_name, None)
    else:
        if c.verbose:
            print "[-] EMUL-ERR file {0} does not have xattr {1}".format(
                    path, xattr_name)
        return 1

    _unsync_inode_by_id(id)

    if c.verbose:
        print "[+] Removed xattr {0} from file {1}".format(xattr_name, path)

def removexattr(argv):
    return removexattr_base(argv, "removexattr", -1)

def lremovexattr(argv):
    return removexattr_base(argv, "lremovexattr", -1)

def fremovexattr(argv):
    if len(argv) < 2:
        _print_err(ERR_ARG, __name__, 2, argv)
        return 1
    fd = argv[0]
    return removexattr_base(argv, "fremovexattr", fd)

def listxattr_base(argv, syscall_name, fd):
    """
    ssize_t listxattr(const char *path, char *list, size_t size);
    - listxattr() retrieves the list of extended attribute names associated
      with the given path in the filesystem.
    - The retrieved list is placed in list, a caller-allocated buffer whose
      size (in bytes) is specified in the argument size.
    - The list is the set of (null-terminated) names, one after the other.
      Names of extended attributes to which the calling process does not have
      access may be omitted from the list.
    - The length of the attribute name list is returned.
    """

    if len(argv) < 3:
        _print_err(ERR_ARG, __name__, 3, argv)
        return 1
    _update_dentry()

    path = ""
    if fd == -1:
        path = _get_path(argv[0])
        if path == None:
            if c.verbose:
                print "[-] EMUL-ERR path not exist"
            return -1
        try:
            id = c.DENTRY[path]
        except KeyError:
            if c.verbose:
                print "[-] EMUL-ERR file {0} does not exist".format(path)
            return -1

    buf_var = argv[1].replace("(long)", "")
    try:
        buf_size = int(c.BUF_SIZE[buf_var])
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR buffer variable {0} is not initialized".format(
                    buf_var)
        return -1
    try:
        buf_data = c.BUF_DATA[buf_var]
    except KeyError:
        buf_data = ""
        pass

    #size = min(buf_size, int(argv[2]))
    size = int(argv[2])

    if buf_size == 0:
        if c.verbose:
            print "[-] EMUL-ERR the buf specified is NULL"
        return -1
    
    inode = None
    if fd == -1:
        try:
            inode = c.MEM[id]
        except KeyError:
            inode = c.DISK[id]
    else:
        inode = _get_inode_of_fd(fd)
        if inode == -1:
            if c.verbose:
                print "[-] EMUL-ERR inode is not found for fd {}".format(fd)
            return -1
        try:
            inode = c.MEM[inode.id]
        except:
            inode = c.DISK[inode.id]

    if inode.type == c.SYMLINK:
        if syscall_name in ["listxattr", "flistxattr"]:
            _, inode = _resolve_symlink_path(path, inode, [])
        elif syscall_name == "llistxattr":
            pass
        if inode == -1:
            return -1
        id = inode.id

    if not inode.xattr:
        if c.verbose:
            print "[-] {0} has no xattr".format(path)
        return -1

    if not check_R_perm(inode.mode):
        if c.verbose:
            print "[-] not have the read permission {}".format(oct(inode.mode))
        return -1

    xattr_name_str = ";".join(sorted(inode.xattr))+";"
    # the list is unordered, so we actually have no way to emulate this
    # but fuzzer-generated testcases tend to assign only one xattr to a file,
    # making us not having to be concerned about the order it appears.

    if len(xattr_name_str) > size:
        if c.verbose:
            print "[-] EMUL-ERR size of xattr list string {0} is larger than the given size {1}".format(len(xattr_name_str), size)
        return -1

    if len(buf_data) >= len(xattr_name_str):
        buf_data = xattr_name_str + buf_data[len(xattr_name_str):]
    else:
        buf_data = xattr_name_str

    c.BUF_DATA[buf_var] = buf_data
    if c.verbose:
        print "[+] listxattr stored xattr list of {0} to {1}".format(
                path, buf_var)

    return len(xattr_name_str)

def listxattr(argv):
    return listxattr_base(argv, "listxattr", -1)

def llistxattr(argv):
    """
    llistxattr()  is  identical to listxattr(),
    except in the case of a symbolic link,
    where the list of names of extended attributes
    associated with the link itself is retrieved,
    not the file that it refers to.
    """
    return listxattr_base(argv, "llistxattr", -1)

def flistxattr(argv):
    
    if len(argv) < 3:
        _print_err(ERR_ARG, __name__, 3, argv)
        return 1
    fd = argv[0]
    
    return listxattr_base(argv, "flistxattr", fd)

def getxattr_base(argv, syscall_name, fd):

    """
       getxattr(const char *path/fd, const char *name,
                void *value, size_t size);

       getxattr():
       The attribute value is placed in the buffer pointed to by value; 
       size  specifies the size of that buffer.
       The return value of the call is the number of bytes placed in value.

       lgetxattr()  is  identical  to getxattr(),
       except in the case of a symbolic link,
       where the link itself is interrogated,
       not the file that it refers to.

       fgetxattr() is identical to getxattr(),
       only the open file referred to by fd is interrogated in place of path.
    """
    if len(argv) < 4:
        _print_err(ERR_ARG, __name__, 4, argv)
        return -1
    _update_dentry()

    inode = None
    path = ""
    if fd == -1:
        path = _get_path(argv[0])
        if path == None:
            if c.verbose:
                print "[-] EMUL-ERR path not exist"
            return -1
        try:
            id = c.DENTRY[path]
        except KeyError:
            if c.verbose:
                print "[-] EMUL-ERR file {0} does not exist".format(path)
            return -1
        try:
            inode = c.MEM[id]
        except KeyError:
            inode = c.DISK[id]
    else:
        inode = _get_inode_of_fd(fd)
        if inode == -1:
            if c.verbose:
                print "[-] EMUL-ERR inode of fd {} doesn't exist".format(fd)
            return -1
    
    xattr_name = _get_assigned_value_of_var(argv[1])
    if xattr_name == -1:
        if c.verbose:
            print "[-] EMUL-ERR invalid xattr name {0}".format(argv[1])
        return -1
    xattr_name = zero_terminiated_str(xattr_name)

    buf_var = argv[2].replace("(long)", "")
    try:
        buf_size = int(c.BUF_SIZE[buf_var])
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR buffer variable {0} is not initialized".format(
                    buf_var)
        return -1
    try:
        buf_data = c.BUF_DATA[buf_var]
    except KeyError:
        buf_data = ""
        pass

    size = int(argv[3])

    if buf_size == 0:
        if c.verbose:
            print "[-] EMUL-ERR the buf specified is NULL"
        return -1    

    if inode.type == c.SYMLINK and syscall_name != "llistxattr":
        _, inode = _resolve_symlink_path(path, inode, [])
        if inode == -1:
            return -1

    if not inode.xattr:
        if c.verbose:
            print "[-] {0} has no xattr".format(path)
        return -1

    try:
        xattr_value_str = inode.xattr[xattr_name]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR xattr {} doesn't exist".format(xattr_name)
        return -1

    if len(xattr_value_str) > size:
        if c.verbose:
            print "[-] EMUL-ERR size of xattr value {0} is larger than the given size {1}".format(len(xattr_value_str), size)
        return -1

    if len(buf_data) >= len(xattr_value_str):
        buf_data = xattr_value_str + buf_data[len(xattr_value_str):]
    else:
        buf_data = xattr_value_str

    c.BUF_DATA[buf_var] = buf_data
    if c.verbose:
        print "[+] listxattr stored xattr list of {0} to {1}".format(
                path, buf_var)

    return len(xattr_value_str)

def getxattr(argv):
    return getxattr_base(argv, "getxattr", -1)

def lgetxattr(argv):
    return getxattr_base(argv, "lgetxattr", -1)

def fgetxattr(argv):
    if len(argv) < 4:
        _print_err(ERR_ARG, __name__, 4, argv)
        return -1
    fd = argv[0]
    return getxattr_base(argv, "fgetxattr", fd)

def dup(argv, varname, ret_dup2=None):
    """
        int dup(int fildes); = fcntl(fildes, F_DUPFD, 0);
        Return a new file descriptor which shall be allocated as described in File Descriptor Allocation, except that it shall be the lowest numbered available file descriptor greater than or equal to the third argument.
    """
    if len(argv) < 1:
        _print_err(ERR_ARG, __name__, 1, argv)
        return 1
    fd = argv[0]
    inode = _get_inode_of_fd(fd)
    if inode == -1:
        if c.verbose:
            print "[-] EMUL-ERR inode of fd {} doesn't exist".format(fd)
        return -1
    c.FD_STACK[varname] = inode
    inode.offset[varname] = 0 # init offset for fd
    inode.opt_dict[varname] = inode.opt_dict[fd]
    # If dup2 has a return value
    if ret_dup2 != None:
        c.FD_STACK[ret_dup2] = inode
        inode.opt_dict[ret_dup2] = inode.opt_dict[fd]
        # TODO: problematic
        inode.offset[ret_dup2] = 0

    inode.refs += 1

def dup2(argv, varname):
    """
    int dup2(int fildes, int fildes2);
    The dup2() function shall cause the file descriptor fildes2 to refer to the same open file description as the file descriptor fildes and to share any locks, and shall return fildes2.
    If fildes2 is already a valid open file descriptor,
    it shall be closed first,
    unless fildes is equal to fildes2
    in which case dup2() shall return fildes2 without closing it.
    
    If the close operation fails to close fildes2, dup2() shall return -1 without changing the open file description to which fildes2 refers. If fildes is not a valid file descriptor, dup2() shall return -1 and shall not close fildes2. If fildes2 is less than 0 or greater than or equal to {OPEN_MAX}, dup2() shall return -1 with errno set to [EBADF].
    """
    if len(argv) < 2:
        _print_err(ERR_ARG, __name__, 2, argv)
        return -1
    fd1 = argv[0]
    fd2 = argv[1]

    # Validate fd1
    inode = _get_inode_of_fd(fd1)
    if inode == -1:
        if c.verbose:
            print "[-] EMUL-ERR inode referred by fd1 doesn't exist"
        return -1

    if fd1 == fd2:
        if c.verbose:
            print "[-] EMUL-ERR fd2 is fd1"
        return
    
    # If fd2 is valid, invalidate it
    _reset_inode_of_fd(fd2)
    dup(argv, fd2, varname)

def getdents(argv):
    """
    int getdents(unsigned int fd, struct linux_dirent *dirp,
                    unsigned int count)
    getdents() reads linux_dirent structures from the directory
    referred  to  by  the "fd" into the buffer pointed to by dirp.
    The argument count specifies the size of that buffer.
    """
    if len(argv) < 3:
        _print_err(ERR_ARG, __name__, 3, argv)
        return -1

    # validate arguments
    fd = argv[0]
    inode = _get_inode_of_fd(fd)
    if inode == -1:
        if c.verbose:
            print "[-] EMUL-ERR invalid fd {}".format(fd)
        return -1

    if inode.type != c.DIR:
        if c.verbose:
            print "[-] EMUL-ERR cannot getdents on a non-dir file"
        return -1

    try:
        buf_var = argv[1].replace("(long)", "")
        buf_size = int(c.BUF_SIZE[buf_var])
        buf_data = c.BUF_DATA[buf_var]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR buffer variable {0} is not initialized".format(buf_var)
        buf_data = ""
        return -1
    if buf_size == 0:
        if c.verbose:
            print "[-] EMUL-ERR dirp buffer is NULL"
        return -1

    count = int(argv[2])

    # Fill the dirp buffer
    """
    struct linux_dirent {
        unsigned long	d_ino;
        unsigned long	d_off;
        unsigned short	d_reclen;
        char		    d_name[];
    };
    """
    all_nodes = inode.p_children + inode.children
    names = []
    for dent in [node for node in all_nodes if node not in inode.d_children]:
        if count < (10+len(dent.name)):
            break
        names.append(dent.name)
    buf_data = ";".join(names)+";"
    c.BUF_DATA[buf_var] = buf_data
    
    return len(buf_data)

def stat_base(argv, syscall_name, fd):

    """
    int stat(const char *pathname, struct stat *statbuf);

    No permissions are required on the file itself,
    but—in the case of stat(), fstatat(), and lstat()—
    execute (search) permission is required on all of the directories in pathname that lead to the file.
    
    lstat() is identical to stat(), except that if pathname is a symbolic link,
    then it returns information about the link itself, not the file that it refers to.
    """

    if len(argv) < 2:
        _print_err(ERR_ARG, __name__, 2, argv)
        return -1
    
    # validate arguments
    inode = None
    path = ""
    if fd == -1:
        path = _get_path(argv[0])
        if path == None:
            if c.verbose:
                print "[-] EMUL-ERR path not exist"
            return -1
        try:
            id = c.DENTRY[path]
        except KeyError:
            if c.verbose:
                print "[-] EMUL-ERR file {0} does not exist".format(path)
            return -1
        try:
            inode = c.MEM[id]
        except KeyError:
            inode = c.DISK[id]
    else:
        fd = argv[0]
        inode = _get_inode_of_fd(fd)
        if inode == -1:
            if c.verbose:
                print "[-] EMUL-ERR invalid fd {}".format(fd)
            return -1

    try:
        buf_var = argv[1].replace("(long)", "")
        buf_size = int(c.BUF_SIZE[buf_var])
        buf_data = c.BUF_DATA[buf_var]
    except KeyError:
        if c.verbose:
            print "[-] EMUL-ERR buffer variable {0} is not initialized".format(buf_var)
        buf_data = ""
        return -1
    if buf_size == 0:
        if c.verbose:
            print "[-] EMUL-ERR dirp buffer is NULL"
        return -1

    if inode.type == c.SYMLINK and syscall_name != "lstat":
        _, inode = _resolve_symlink_path(path, inode, [])
        if inode == -1:
            if c.verbose:
                print "[-] EMUL-ERR failed to resolve the symlink path"
            return -1

    """
    struct stat {
        dev_t     st_dev;         /* ID of device containing file */
        ino_t     st_ino;         /* Inode number */
        mode_t    st_mode;        /* File type and mode */
        nlink_t   st_nlink;       /* Number of hard links */
        uid_t     st_uid;         /* User ID of owner */
        gid_t     st_gid;         /* Group ID of owner */
        dev_t     st_rdev;        /* Device ID (if special file) */
        off_t     st_size;        /* Total size, in bytes */
        blksize_t st_blksize;     /* Block size for filesystem I/O */
        blkcnt_t  st_blocks;      /* Number of 512B blocks allocated */
        struct timespec st_atim;  /* Time of last access */
        struct timespec st_mtim;  /* Time of last modification */
        struct timespec st_ctim;  /* Time of last status change */
    }
    """
    if c.verbose:
        print("Stat: type", inode.type, "mode", inode.mode, "linkcnt",
            inode.linkcnt, "size", inode.size)
    buf_data = str(inode.mode | inode.type) + \
            str(inode.linkcnt) + str(inode.size)
    c.BUF_DATA[buf_var] = buf_data

    return len(buf_data)

def stat(argv):
    return stat_base(argv, "stat", -1)

def lstat(argv):
    return stat_base(argv, "lstat", -1)

def fstat(argv):
    if len(argv) < 2:
        _print_err(ERR_ARG, __name__, 2, argv)
        return -1
    fd = argv[0]
    return stat_base(argv, "fstat", fd)


def syz_failure_down(argv, node_idx):
    c.NODESTATE[node_idx] = 'down'

def syz_failure_up(argv, node_idx):
    c.NODESTATE[node_idx] = 'up'


def ip_difference(ip1, ip2):
    # Convert IP addresses to single integers
    def ip_to_int(ip):
        parts = list(map(int, ip.split('.')))
        return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]

    ip1_num = ip_to_int(ip1)
    ip2_num = ip_to_int(ip2)

    # Calculate the difference
    if ip1_num > ip2_num:
        raise ValueError("The first IP address should be smaller than the second one.")
    
    return ip2_num - ip1_num

def syz_failure_net_down(argv, node_idx):
    # iptables -A INPUT -s 192.168.0.6 -j DROP;iptables -A OUTPUT -d 192.168.0.6 -j DROP;
    iptable_cmd = _get_assigned_value_of_var(argv[0])
    for cmd in iptable_cmd.split(';'):
        print(cmd)
        if cmd == "":
            continue
        ip = cmd.split(" ")[4]
        print(c.FSCFG["init_ip"], ip)
        part_node_idx = ip_difference(c.FSCFG["init_ip"], ip)
        c.NETSTATE.append((node_idx, part_node_idx))

def syz_failure_net_up(argv, node_idx):
    del c.NETSTATE[:]

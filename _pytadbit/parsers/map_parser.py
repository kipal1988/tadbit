"""
22 may 2015
"""

from pytadbit.utils.file_handling import magic_open
from bisect import bisect_left as bisect
from pytadbit.mapping.restriction_enzymes import map_re_sites
from warnings import warn

def parse_map(f_names1, f_names2=None, out_file1=None, out_file2=None,
              genome_seq=None, re_name=None, verbose=False, **kwargs):
    """
    Parse map files

    Keep a summary of the results into 2 tab-separated files that will contain 6
       columns: read ID, Chromosome, position, strand (either 0 or 1), mapped
       sequence lebgth, position of the closest upstream RE site, position of
       the closest downstream RE site

    :param f_names1: a list of path to sam/bam files corresponding to the
       mapping of read1, can also  be just one file
    :param f_names1: a list of path to sam/bam files corresponding to the
       mapping of read2, can also  be just one file
    :param out_file1: path to outfile tab separated format containing mapped
       read1 information
    :param out_file1: path to outfile tab separated format containing mapped
       read2 information
    :param genome_seq: a dictionary generated by :func:`pyatdbit.parser.genome_parser.parse_fasta`.
       containing the genomic sequence
    :param re_name: name of the restriction enzyme used
    """
    # not nice, dirty fix in order to allow this function to only parse
    # one SAM file
    if not out_file1:
        raise Exception('ERROR: out_file1 should be given\n')
    if not re_name:
        raise Exception('ERROR: re_name should be given\n')
    if not genome_seq:
        raise Exception('ERROR: genome_seq should be given\n')
    if (f_names2 and not out_file2) or (not f_names2 and out_file2):
        raise Exception('ERROR: out_file2 AND f_names2 needed\n')

    frag_chunk = kwargs.get('frag_chunk', 100000)
    if verbose:
        print 'Searching and mapping RE sites to the reference genome'
    frags = map_re_sites(re_name, genome_seq, frag_chunk=frag_chunk,
                         verbose=verbose)

    if isinstance(f_names1, str):
        f_names1 = [f_names1]
    if isinstance(f_names2, str):
        f_names2 = [f_names2]
    if f_names2:
        fnames = f_names1, f_names2
        outfiles = out_file1, out_file2
    else:
        fnames = (f_names1,)
        outfiles = (out_file1, )

    for read in range(len(fnames)):
        if verbose:
            print 'Loading read' + str(read + 1)
        windows = {}
        reads    = []
        num = 0
        for fnam in fnames[read]:
            try:
                fhandler = magic_open(fnam)
            except IOError:
                warn('WARNING: file "%s" not found\n' % fnam)
                continue
            # get the iteration number of the iterative mapping
            try:
                num = int(fnam.split('.')[-1].split(':')[0])
            except:
                num += 1
            windows.setdefault(num, 0)
            if verbose:
                print 'loading file: %s' % (fnam)
            # iteration over reads
            for r in fhandler:
                name, seq, _, _, ali = r.split('\t')[:5]
                crm, strand, pos = ali.split(':')[:3]
                positive = strand == '+'
                len_seq  = len(seq)
                if positive:
                    pos = int(pos)
                else:
                    pos = int(pos) + len_seq - 1 # remove 1 because all inclusive
                try:
                    frag_piece = frags[crm][pos / frag_chunk]
                except KeyError:
                    # Chromosome not in hash
                    continue
                idx = bisect(frag_piece, pos)
                try:
                    next_re = frag_piece[idx]
                except IndexError:
                    # case where part of the read is mapped outside chromosome
                    count = 0
                    while idx >= len(frag_piece) and count < len_seq:
                        pos -= 1
                        count += 1
                        frag_piece = frags[crm][pos / frag_chunk]
                        idx = bisect(frag_piece, pos)
                    if count >= len_seq:
                        raise Exception('Read mapped mostly outside ' +
                                        'chromosome\n')
                    next_re    = frag_piece[idx]
                prev_re    = frag_piece[idx - 1 if idx else 0]
                reads.append('%s\t%s\t%d\t%d\t%d\t%d\t%d\n' % (
                    name, crm, pos, positive, len_seq, prev_re, next_re))
                windows[num] += 1
        reads_fh = open(outfiles[read], 'w')
        ## write file header
        # chromosome sizes (in order)
        reads_fh.write('## Chromosome lengths (order matters):\n')
        for crm in genome_seq:
            reads_fh.write('# CRM %s\t%d\n' % (crm, len(genome_seq[crm])))
        reads_fh.write('## Number of mapped reads by iteration\n')
        for size in windows:
            reads_fh.write('# MAPPED %d %d\n' % (size, windows[size]))
        reads.sort()
        prev_head = reads[0].split('\t', 1)[0]
        prev_read = reads[0].strip()
        for read in reads[1:]:
            head = read.split('\t', 1)[0]
            if head == prev_head:
                prev_read += '|||' + read.strip()
            else:
                reads_fh.write(prev_read + '\n')
                prev_read = read.strip()
            prev_head = head
        reads_fh.write(prev_read + '\n')
        reads_fh.close()
    del reads


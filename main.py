from __future__ import division
import numpy as np
import scipy.sparse as sp
import logging
import pickle
import argparse 
import yaml
import sys
import os
import matplotlib.pyplot as plt

log = logging.getLogger('main');
log.setLevel(logging.DEBUG);

def pdbgen(fulldat, resname, filename):
	
    numatom, numsamp = fulldat.shape;
    numatom = numatom // 3;
    assert ( len(resname) == numatom );

    log.info('Constructing PDB file... \'{0}\''.format(filename));
    f = open(filename, 'w+');
    for i in range(numsamp):
        f.write('%-6s    %4i\n' %('MODEL', i+1));
        for j in range(numatom):
            f.write('%-6s%5i %4s %s  %4i    %8.3f%8.3f%8.3f%6.2f%6.2f          %2s  \n' \
				%('ATOM', j+1, 'CA', resname[j], j+1, fulldat[3*j,i], fulldat[3*j+1,i], fulldat[3*j+2,i], 0.0, 0.0, 'C'));
        f.write('ENDMDL\n');
    f.close();
    log.info('PDB file completed!');

def _get_anharm( data, function ):

    data = np.abs(data) > function(data);
    num = np.sum(data);
    indices = np.argsort( - data )[:num];

    return list(indices), num;

def analyze( config ):

    coords =    np.load(config['coords']);
    resnames =  np.load(config['resnames']);
    icacoffs = np.load( config['icacoffs'] );
    num_mat = np.zeros((icacoffs.shape[0], 4));
    data_mat = np.empty( shape=(icacoffs.shape[0], 4), dtype=list );
    func = [];
    func.append( lambda x: np.mean(x) );
    for i in range(1,4):
        func.append( lambda x: i*np.std(x) );
    for i in range(icacoffs.shape[0]):
        for j in range(4):
            data_mat[i,j], num_mat[i,j] = _get_anharm( icacoffs[i], func[j] );

    if not os.path.isdir( config['saveDir'] ):
        os.makedirs( config['saveDir'] );    
    if not os.path.isdir( config['figDir'] ):
        os.makedirs( config['figDir'] );   

    np.save( os.path.join(config['saveDir'], '{0}_num_anharm.npy'.format(config['pname'])), num_mat);
    np.save( os.path.join(config['saveDir'], '{0}_anharm_groups.npy'.format(config['pname'])), data_mat);
    pdbpath = os.path.join( config['saveDir'], 'pdbfiles' );

    #   Plotting
    color = ['black', 'green', 'blue', 'red'];
    for i in range(icacoffs.shape[0]):
        fig = plt.figure();
        ax = fig.gca();
        ax.plot(np.abs(icacoffs[i]), color='black');
        stat = [];
        for j in range(4):
            stat.append( func[j](icacoffs[i] ) );
            ax.plot(stat[j], color=color[j]);
        ax.set_title('ICA Anharmonicity: Moment {0}'.format(i));
        ax.set_xlabel('Conformation');
        ax.annotate('Mean', xy=(0,stat[0]), xytext=(5, stat[0] - 5),);
        for j in range(1,4):
            ax.annotate('Std. Dev * {0}'.format(j), xy=(0, stat[j]), xytext=(5, stat[j]*(1+1/j)),);
        plt.savefig( os.path.join(config['figDir'], '{0}_anharm_moment{1}.png'.format(config['pname'], i)) );
        pickle.dump( fig, file( os.path.join(config['figDir'], '{0}_anharm_moment{1}.png'.format(config['pname'], i)), 'w+') );
        if 'graph' in config and config['graph']:
            plt.show();

    if not os.path.isdir( pdbpath ):
        os.makedirs( pdbpath );
    for i in range( icacoffs.shape[0] ):
        print coords.shape; 
        print resnames.shape;
        pdbgen( coords[:,data_mat[i,2]], resnames, os.path.join(pdbpath, 'anharm_conform_moment{0}.pdb'.format(i)) );
        


if __name__ == '__main__':

    #   Setup parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-g', action='store_true', dest='graph', default=False, help='Shows graphs.');
    parser.add_argument('-v', action='store_true', dest='verbose', default=False, help='Runs program verbosely.');
    parser.add_argument('-d', '--debug', action='store_true', dest='debug', default=False, help='Prints debugging help.');
    parser.add_argument('--config', type=str, dest='configpath', default='config.yaml',
                        help='Input other configuration file.');

    values = parser.parse_args()

    #   Get config from file
    with open(values.configpath) as f:
        conf_file = f.read();
        config = yaml.load(conf_file);
    if not 'config' in locals(): raise IOError(
    'Issue opening and reading configuration file: {0}'.format(os.path.abspath(values.configpath)) );

    #   Update config with CLARGS
    level = 30;
    if values.verbose: level = 20;
    elif values.debug: level = 10;
    config['graph'] = values.graph;

    #   Setup stream logger
    ch = logging.StreamHandler(sys.stdout);
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s');
    ch.setLevel(level);
    ch.setFormatter(formatter);

    log.addHandler(ch);

    log.debug('Configuration File:\n'+conf_file);
    log.info('Using Configuration File: {0}'.format(os.path.abspath(values.configpath)));

    if not os.path.isfile( config['icacoffs'] ):
        raise IOError( 'Error opening icacoffs file: {0}'.format(os.path.abspath(config['icacoffs'])) );

    analyze( config );
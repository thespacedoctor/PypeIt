# Odds and ends in support of tests
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import pytest

from pypeit import arcimage
from pypeit import traceslits
from pypeit import wavecalib
from pypeit import wavetilts
from pypeit.spectrographs.util import load_spectrograph

# Create a decorator for tests that require the PypeIt dev suite
dev_suite_required = pytest.mark.skipif(os.getenv('PYPEIT_DEV') is None,
                                        reason='test requires dev suite')

def data_path(filename):
    data_dir = os.path.join(os.path.dirname(__file__), 'files')
    return os.path.join(data_dir, filename)


def load_kast_blue_masters(get_spectrograph=False, aimg=False, tslits=False, tilts=False,
                           datasec=False, wvcalib=False):

    spectrograph = load_spectrograph('shane_kast_blue')
    spectrograph.naxis = (2112,350)     # Image shape with overscan

    root_path = data_path('MF') if os.getenv('PYPEIT_DEV') is None \
                    else os.path.join(os.getenv('PYPEIT_DEV'), 'Cooked', 'MF')
    master_dir = root_path+'_'+spectrograph.spectrograph

    mode = 'reuse'

    # Load up the Masters
    ret = []

    if get_spectrograph:
        ret.append(spectrograph)

    setup = 'A_01_aa'
    if aimg:
        AImg = arcimage.ArcImage(spectrograph, setup=setup, master_dir=master_dir, mode=mode)
        msarc = AImg.load_master(AImg.ms_name)
        ret.append(msarc)

    if tslits:
        traceSlits = traceslits.TraceSlits(None,None)
        traceSlits.load_master(os.path.join(master_dir,'MasterTrace_A_01_aa'))
        ret.append(traceSlits.tslits_dict)

    if tilts:
        wvTilts = wavetilts.WaveTilts(None, spectrograph=spectrograph, setup=setup,
                                      master_dir=master_dir, mode=mode)
        tilts_dict = wvTilts.master()
        ret.append(tilts_dict)

    if datasec:
        datasec_img = spectrograph.get_datasec_img(data_path('b1.fits.gz'), 1)
        ret.append(datasec_img)

    if wvcalib:
        Wavecalib = wavecalib.WaveCalib(None, spectrograph=spectrograph, setup=setup,
                                        master_dir=master_dir, mode=mode)
        wv_calib = Wavecalib.master()
        ret.append(wv_calib)

    # Return
    return ret

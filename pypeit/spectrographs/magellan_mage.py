""" Module for Magellan/MAGE specific codes
"""
import numpy as np

from pypeit import msgs
from pypeit import telescopes
from pypeit.core import framematch
from pypeit.core import parse
from pypeit.par import pypeitpar
from pypeit.spectrographs import spectrograph
from pypeit.core import pixels
from pypeit import debugger

class MagellanMAGESpectrograph(spectrograph.Spectrograph):
    """
    Child to handle Magellan/MAGE specific code
    """
    def __init__(self):
        # Get it started
        super(MagellanMAGESpectrograph, self).__init__()
        self.spectrograph = 'magellan_mage'
        self.telescope = telescopes.MagellanTelescopePar()
        self.camera = 'MAGE'
        self.numhead = 1
        self.detector = [
                # Detector 1
                pypeitpar.DetectorPar(
                            specaxis        = 0,
                            specflip        = False,
                            xgap            = 0.,
                            ygap            = 0.,
                            ysize           = 1.,
                            # plate scale in arcsec/pixel
                            platescale      = 0.3,
                            # electrons/pixel/hour. From: http://www.lco.cl/telescopes-information/magellan/instruments/mage/the-mage-spectrograph-user-manual
                            darkcurr        = 1.00,
                            saturation      = 65535.,
                            # CCD is linear to better than 0.5 per cent up to digital saturation (65,536 DN including bias) in the Fast readout mode.
                            nonlinear       = 0.99,
                            numamplifiers   = 1,
                            gain            = 1.02, # depends on the readout
                            ronoise         = 2.9, # depends on the readout
                            datasec         = '[1:2048,1:1024]',      # complementary to oscansec
                            oscansec        = '[2049:2176,1025:1152]' # as taken from the header
                            )]
        # Taken from the MASE paper: https://arxiv.org/pdf/0910.1834.pdf
        self.norders = 15 
        # Uses default timeunit
        # Uses default primary_hdrext
        # self.sky_file = ?

    @property
    def pypeline(self):
        return 'Echelle'

    def default_pypeit_par(self):
        """
        Set default parameters for magellan MagE reduction.
        """
        par = pypeitpar.PypeItPar()
        par['rdx']['spectrograph'] = 'magellan_mage'
        # Frame numbers
        par['calibrations']['standardframe']['number'] = 1
        par['calibrations']['biasframe']['number'] = 0
        par['calibrations']['pixelflatframe']['number'] = 3
        par['calibrations']['traceframe']['number'] = 3
        par['calibrations']['arcframe']['number'] = 1
        # Bias
        par['calibrations']['biasframe']['useframe'] = 'overscan'
        # Wavelengths
        # 1D wavelength solution
        par['calibrations']['wavelengths']['rms_threshold'] = 0.20  # Might be grating dependent..
        par['calibrations']['wavelengths']['sigdetect']=5.0
        par['calibrations']['wavelengths']['lamps'] = ['ThAr']
        par['calibrations']['wavelengths']['nonlinear_counts'] = self.detector[0]['nonlinear'] * self.detector[0]['saturation']

        #par['calibrations']['wavelengths']['method'] = 'reidentify'

        # Reidentification parameters
        #par['calibrations']['wavelengths']['reid_arxiv'] = 'magellan_thar.json'
        par['calibrations']['wavelengths']['ech_fix_format'] = True
        # Echelle parameters
        par['calibrations']['wavelengths']['echelle'] = True
        par['calibrations']['wavelengths']['ech_nspec_coeff'] = 4
        par['calibrations']['wavelengths']['ech_norder_coeff'] = 4
        par['calibrations']['wavelengths']['ech_sigrej'] = 3.0

        # Always correct for flexure, starting with default parameters
        par['flexure'] = pypeitpar.FlexurePar()
        par['scienceframe']['process']['sigclip'] = 20.0
        par['scienceframe']['process']['satpix'] ='nothing'


        # Set slits and tilts parameters
#        par['calibrations']['tilts']['order'] = 2
        par['calibrations']['tilts']['tracethresh'] = [10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]
        par['calibrations']['slits']['trace_npoly'] = 5
        par['calibrations']['slits']['maxshift'] = 3.
        par['calibrations']['slits']['pcatype'] = 'order'
        # Scienceimage default parameters
        par['scienceimage'] = pypeitpar.ScienceImagePar()
        # Always flux calibrate, starting with default parameters
        par['fluxcalib'] = pypeitpar.FluxCalibrationPar()
        # Do not correct for flexure
        par['flexure'] = pypeitpar.FlexurePar()
        par['flexure']['method'] = 'skip'
        # Set the default exposure time ranges for the frame typing
        par['calibrations']['standardframe']['exprng'] = [None, 20]
        par['calibrations']['arcframe']['exprng'] = [20, None]
        par['calibrations']['darkframe']['exprng'] = [20, None]
        par['scienceframe']['exprng'] = [20, None]
        return par

    def init_meta(self):
        """
        Generate the meta data dict
        Note that the children can add to this

        Returns:
            self.meta: dict (generated in place)

        """
        self.meta = {}
        # Required (core)
        self.meta['ra'] = dict(ext=0, card='RA')
        self.meta['dec'] = dict(ext=0, card='DEC')
        self.meta['target'] = dict(ext=0, card='OBJECT')
        #TODO: Check decker is correct
        self.meta['decker'] = dict(ext=0, card='SLITENC')
        self.meta['binning'] = dict(card=None, compound=True)
#        self.meta['binning'] = dict(ext=0, card='BINNING')
        self.meta['mjd'] = dict(ext=0, card='MJD-OBS')
        self.meta['exptime'] = dict(ext=0, card='EXPTIME')
        self.meta['airmass'] = dict(ext=0, card='AIRMASS')
        # Extras for config and frametyping
        self.meta['dispname'] = dict(ext=0, card='INSTR')

    def compound_meta(self, headarr, meta_key):
        """

        Args:
            headarr: list
            meta_key: str

        Returns:
            value

        """
        if meta_key == 'binning':
            binspatial, binspec = parse.parse_binning(headarr[0]['BINNING'])
            return parse.binning2string(binspec, binspatial)

    def check_frame_type(self, ftype, fitstbl, exprng=None):
        """
        Check for frames of the provided type.
        """
        # TODO: arcs, tilts, darks?
        if ftype in ['pinhole', 'bias']:
            # No pinhole or bias frames
            return np.zeros(len(fitstbl), dtype=bool)
        if ftype in ['pixelflat', 'trace']:
            return fitstbl['idname'] == 'domeflat'
        
        return (fitstbl['idname'] == 'object') \
                        & framematch.check_frame_exptime(fitstbl['exptime'], exprng)

    def bpm(self, shape=None, filename=None, det=None, **null_kwargs):
        """
        Override parent bpm function with BPM specific to X-Shooter VIS.

        .. todo::
            Allow for binning changes.

        Parameters
        ----------
        det : int, REQUIRED
        **null_kwargs:
            Captured and never used

        Returns
        -------
        bpix : ndarray
          0 = ok; 1 = Mask

        """
        msgs.info("Custom bad pixel mask for MAGE")
        self.empty_bpm(shape=shape, filename=filename, det=det)
        if det == 1:
            self.bpm_img[:, :20] = 1.
            self.bpm_img[:, 1000:] = 1.

        return self.bpm_img

    @staticmethod
    def slitmask(tslits_dict, pad=None, binning=None):
        """
         Generic routine ton construct a slitmask image from a tslits_dict. Children of this class can
         overload this function to implement instrument specific slitmask behavior, for example setting
         where the orders on an echelle spectrograph end

         Parameters
         -----------
         tslits_dict: dict
            Trace slits dictionary with slit boundary information

         Optional Parameters
         pad: int or float
            Padding of the slit boundaries
         binning: tuple
            Spectrograph binning in spectral and spatial directions

         Returns
         -------
         slitmask: ndarray int
            Image with -1 where there are no slits/orders, and an integer where there are slits/order with the integer
            indicating the slit number going from 0 to nslit-1 from left to right.

         """

        # These lines are always the same
        pad = tslits_dict['pad'] if pad is None else pad
        slitmask = pixels.slit_pixels(tslits_dict['lcen'], tslits_dict['rcen'], tslits_dict['nspat'], pad=pad)

        spec_img = np.outer(np.arange(tslits_dict['nspec'], dtype=int), np.ones(tslits_dict['nspat'], dtype=int))  # spectral position everywhere along image

        order7bad = (slitmask == 0) & (spec_img < tslits_dict['nspec']/2)
        slitmask[order7bad] = -1
        return slitmask

    @staticmethod
    def slit2order(islit):

        """
        Parameters
        ----------
        islit: int, float, or string, slit number

        Returns
        -------
        order: int
        """

        if isinstance(islit, str):
            islit = int(islit)
        elif isinstance(islit, np.ndarray):
            islit = islit.astype(int)
        elif isinstance(islit, float):
            islit = int(islit)
        elif isinstance(islit, int):
            pass
        else:
            msgs.error('Unrecognized type for islit')

        orders = np.arange(7, 2, -1, dtype=int)
        return orders[islit]

    @staticmethod
    def order_platescale(binning = None):


        """
        Returns the plate scale in arcseconds for each order

        Parameters
        ----------
        None

        Optional Parameters
        --------------------
        binning: str

        Returns
        -------
        order_platescale: ndarray, float

        """

        # MAGE has no binning, but for an instrument with binning we would do this
        #binspatial, binspectral = parse.parse_binning(binning)
        return np.full(5, 0.15)


    def bpm(self, shape=None, filename=None, det=None, **null_kwargs):
        """
        Override parent bpm function with BPM specific to X-ShooterNIR.

        .. todo::
            Allow for binning changes.

        Parameters
        ----------
        det : int, REQUIRED
        **null_kwargs:
            Captured and never used

        Returns
        -------
        bpix : ndarray
          0 = ok; 1 = Mask

        """

        self.empty_bpm(shape=shape, filename=filename, det=det)
        return self.bpm_img

    @staticmethod
    def slit2order(islit):

        """
        Parameters
        ----------
        islit: int, float, or string, slit number

        Returns
        -------
        order: int
        """

        if isinstance(islit,str):
            islit = int(islit)
        elif isinstance(islit,np.ndarray):
            islit = islit.astype(int)
        elif isinstance(islit,float):
            islit = int(islit)
        elif isinstance(islit, int):
            pass
        else:
            msgs.error('Unrecognized type for islit')

        orders = np.arange(26,10,-1, dtype=int)
        return orders[islit]

    @staticmethod
    def order_platescale(self, binning = None):


        """
        Returns the plate scale in arcseconds for each order

        Parameters
        ----------
        None

        Optional Parameters
        --------------------
        binning: str

        Returns
        -------
        order_platescale: ndarray, float

        """

        # NIR has no binning, but for an instrument with binning we would do this
        #binspatial, binspectral = parse.parse_binning(binning)

        # ToDO Either assume a linear trend or measure this
        # X-shooter manual says, but gives no exact numbers per order.
        # NIR: 52.4 pixels (0.210”/pix) at order 11 to 59.9 pixels (0.184”/pix) at order 26.

        # Right now I just took the average
        return np.full(16, 0.197)




    @staticmethod
    def slitmask(tslits_dict, pad=None, binning=None):
        """
         Generic routine ton construct a slitmask image from a tslits_dict. Children of this class can
         overload this function to implement instrument specific slitmask behavior, for example setting
         where the orders on an echelle spectrograph end

         Parameters
         -----------
         tslits_dict: dict
            Trace slits dictionary with slit boundary information

         Optional Parameters
         pad: int or float
            Padding of the slit boundaries
         binning: tuple
            Spectrograph binning in spectral and spatial directions

         Returns
         -------
         slitmask: ndarray int
            Image with -1 where there are no slits/orders, and an integer where there are slits/order with the integer
            indicating the slit number going from 0 to nslit-1 from left to right.

         """

        # These lines are always the same
        pad = tslits_dict['pad'] if pad is None else pad
        slitmask = pixels.slit_pixels(tslits_dict['lcen'], tslits_dict['rcen'], tslits_dict['nspat'], pad=pad)

        spec_img = np.outer(np.arange(tslits_dict['nspec'], dtype=int), np.ones(tslits_dict['nspat'], dtype=int))  # spectral position everywhere along image

        nslits = tslits_dict['lcen'].shape[1]
        # These are the order boundaries determined by eye by JFH. 2025 is used as the maximum as the upper bit is not illuminated
        order_max = [1476,1513,1551, 1592,1687,1741,1801, 1864,1935,2007, 2025, 2025,2025,2025,2025,2025]
        order_min = [418 ,385 , 362,  334, 303, 268, 230,  187, 140,  85,   26,    0,   0,   0,   0,   0]
        # TODO add binning adjustments to these
        for islit in range(nslits):
            orderbad = (slitmask == islit) & ((spec_img < order_min[islit]) | (spec_img > order_max[islit]))
            slitmask[orderbad] = -1
        return slitmask









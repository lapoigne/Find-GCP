#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
    GCP finder in a serie of images using opencv aruco markers
    (c) Zoltan Siki siki (dot) zoltan (at) epito.bme.hu
    This code based on
    https://mecaruco2.readthedocs.io/en/latest/notebooks_rst/Aruco/aruco_basics.html
    for details see:
    https://docs.opencv.org/trunk/d5/dae/tutorial_aruco_detection.html

    for usage help:
    gcp_find.py --help
"""
import sys
import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
import cv2
from cv2 import aruco

class GcpFind():
    """ class to collect GCPs on an image """

    def __init__(self, args, params, parser):
        """ Initialize GcpFind object

            :param args: processed command line parameters
            :param params: aruco find param
            :param parser: parser object to print help
        """
        self.args = args
        # prepare aruco
        if args.dict == 99:     # use special 3x3 dictionary
            self.aruco_dict = aruco.Dictionary_create(32, 3)
        else:
            self.aruco_dict = aruco.Dictionary_get(args.dict)
        self.coords = {}
        self.gcp_found = {}          # initialize gcp to image dict
        if args.list:
            # list available aruco dictionary names & exit
            for act_dict in self.list_dicts():
                print('{} : {}'.format(act_dict[0], act_dict[1]))
            sys.exit(0)
        if not self.check_params():
            parser.print_help()
            sys.exit(1)

        if self.args.input:
            self.coo_input()

        if args.type == 'ODM' and args.epsg is not None:
            # write epsg code to the beginning of the output
            self.foutput.write('EPSG:{}\n'.format(args.epsg))

        # set aruco parameters from command line arguments
        self.params = params
        self.params.detectInvertedMarker = args.inverted
        self.params.adaptiveThreshWinSizeMin = args.winmin
        self.params.adaptiveThreshWinSizeMax = args.winmax
        self.params.adaptiveThreshWinSizeStep = args.winstep
        self.params.adaptiveThreshConstant = args.thres
        self.params.minMarkerPerimeterRate = args.minrate
        self.params.maxMarkerPerimeterRate = args.maxrate
        self.params.polygonalApproxAccuracyRate = args.poly
        self.params.minCornerDistanceRate = args.corner
        self.params.minMarkerDistanceRate = args.markerdist
        self.params.minDistanceToBorder = args.borderdist
        self.params.markerBorderBits = args.borderbits
        self.params.minOtsuStdDev = args.otsu
        self.params.perspectiveRemovePixelPerCell = args.persp
        self.params.perspectiveRemoveIgnoredMarginPerCell = args.ignore
        self.params.maxErroneousBitsInBorderRate = args.error
        self.params.errorCorrectionRate = args.correct
        self.params.cornerRefinementMethod = args.refinement
        self.params.cornerRefinementWinSize = args.refwin
        self.params.cornerRefinementMaxIterations = args.maxiter
        self.params.cornerRefinementMinAccuracy = args.minacc

    @staticmethod
    def list_dicts():
        """ collects available aruco dictionary names

            :return: sorted list of available AruCo dictionaries
        """
        dict_list = [(99, 'DICT_3X3_32 custom')]
        for name in aruco.__dict__:
            if name.startswith('DICT_'):
                dict_list.append((aruco.__dict__[name], name))
        return sorted(dict_list)

    def check_params(self):
        """ check command line params

            :return: False in case of parameter error
        """
        if not self.args.names:
            print("no input images given")
            return False
        if self.args.output == sys.stdout:
            self.foutput = args.output
        else:
            try:
                self.foutput = open(args.output, 'w')
            except:
                print('cannot open output file')
                return False
        if self.args.input:
            try:
                self.finput = open(args.input, 'r')
            except:
                print('cannot open input file')
                return False
        return True

    def coo_input(self):
        """ load world coordinates of GCPs
            input file format: point_id easting northing elevation
            coordinates are stored in coords dict
        """
        for line in self.finput:
            co_list = line.strip().split(args.separator)
            if len(co_list) < 4:
                print("Illegal input: {}".format(line))
                continue
            self.coords[int(co_list[0])] = [float(x) for x in co_list[1:4]]
        self.finput.close()

    def process_images(self):
        """ process all images """
        # process image files from command line
        for f_name in self.args.names:
            # read actual image file
            if self.args.verbose:
                print("processing {}".format(f_name))
            self.process_image(f_name)
        if self.args.verbose:
            for j in self.gcp_found:
                print('GCP{}: on {} images {}'.format(j, len(self.gcp_found[j]), self.gcp_found[j]))
        self.foutput.close()

    def process_image(self, image_name):
        """ proces single image

            :param image_name: path to image to process
        """
        frame = cv2.imread(image_name)
        if frame is None:
            print('error reading image: {}'.format(image_name))
            return
        # convert image to gray
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # find markers
        corners, ids, _ = aruco.detectMarkers(gray,
                                              self.aruco_dict,
                                              parameters=self.params)
        if ids is None:
            print('No markers found on image {}'.format(image_name))
            return
        # check duplicate ids
        idsl = [pid[0] for pid in ids]
        if len(ids) - len(set(idsl)):
            print('duplicate markers on image {}'.format(image_name))
            print('marker ids: {}'.format(sorted(idsl)))
        # calculate center & output found markers
        if self.args.verbose:
            print('  {} GCP markers found'.format(ids.size))
        if self.args.debug:  # show found ids in debug mode
            plt.figure()
            plt.title("{} GCP, {} duplicate found on {}".format(len(ids), len(ids) - len(set(idsl)), image_name))
            aruco.drawDetectedMarkers(frame, corners, ids)
            plt.imshow(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        for i in range(ids.size):
            j = ids[i][0]
            if j not in self.gcp_found:
                self.gcp_found[j] = []
            self.gcp_found[j].append(image_name)
            # calculate center of aruco code
            x = int(round(np.average(corners[i][0][:, 0])))
            y = int(round(np.average(corners[i][0][:, 1])))
            if self.args.type == 'ODM':
                if j in self.coords:
                    self.foutput.write('{:.3f} {:.3f} {:.3f} {} {} {} {}\n'.format(
                        self.coords[j][0], self.coords[j][1], self.coords[j][2],
                        x, y, os.path.basename(image_name), j))
                else:
                    print("No coordinates for {}".format(j))
            elif self.args.type == 'VisualSfM':
                if j in self.coords:
                    self.foutput.write('{} {} {} {:.3f} {:.3f} {:.3f}\n'.format(
                        os.path.basename(image_name), x, y,
                        self.coords[j][0], self.coords[j][1], self.coords[j][2]))
                else:
                    print("No coordinates for {}".format(j))
            else:
                if j in self.coords:
                    self.foutput.write('{:.3f} {:.3f} {:.3f} {} {} {}\n'.format(
                        self.coords[j][0], self.coords[j][1], self.coords[j][2],
                        x, y, os.path.basename(image_name)))
                else:
                    self.foutput.write('{} {} {} {}\n'.format(j, x, y,
                                                              os.path.basename(image_name)))
            if self.args.debug:
                if j in self.coords:
                    plt.plot(x, y, "ro", markersize=self.args.markersize,
                             markeredgecolor='y', markeredgewidth=3)
                else:
                    plt.plot(x, y, "r^", markersize=self.args.markersize,
                             markeredgecolor='y', markeredgewidth=3)
                plt.text(x+self.args.markersize, y, str(ids[i][0]),
                         color='y', weight='bold', fontsize=args.fontsize)
                plt.text(x+self.args.markersize, y, str(ids[i][0]),
                         color='r', weight='normal', fontsize=args.fontsize)
        if args.debug:
            #plt.legend()
            plt.show()


def cmd_params(parser, params):
    """ set up command line argument parser
    
        :param parser: command line parser object
        :param params: ArUco parameters for defaults
    0"""
    def_dict = aruco.DICT_4X4_100   # default dictionary 4X4
    def_output = sys.stdout         # default output to stdout
    def_input = None                # default no input coordinates
    def_separator = " "             # default separator is space
    def_type = ""                   # default output type
    def_markersize = 10             # marker size of debug image
    def_fontsize = 6                # marker size of debug image

    parser.add_argument('names', metavar='file_names', type=str, nargs='*',
                        help='image files to process')
    parser.add_argument('-d', '--dict', type=int, default=def_dict,
                        help='marker dictionary id, default={} (DICT_4X4_100)'.format(def_dict))
    parser.add_argument('-o', '--output', type=str, default=def_output,
                        help='name of output GCP list file, default stdout')
    parser.add_argument('-t', '--type', choices=['ODM', 'VisualSfM'],
                        default=def_type,
                        help='target program ODM or VisualSfM, default {}'.format(def_type))
    parser.add_argument('-i', '--input', type=str, default=def_input,
                        help='name of input GCP coordinate file, default {}'.format(def_input))
    parser.add_argument('-s', '--separator', type=str, default=' ',
                        help='input file separator, default {}'.format(def_separator))
    parser.add_argument('-v', '--verbose', action="store_true",
                        help='verbose output to stdout')
    parser.add_argument('-r', '--inverted', action="store_true",
                        help='detect inverted markers')
    parser.add_argument('--debug', action="store_true",
                        help='show detected markers on image')
    parser.add_argument('--markersize', type=int, default=def_markersize,
                        help='marker size on debug image, use together with debug')
    parser.add_argument('--fontsize', type=int, default=def_fontsize,
                        help='font size on debug image, use together with debug')
    parser.add_argument('--winmin', type=int,
                        default=params.adaptiveThreshWinSizeMin,
                        help='adaptive tresholding window min size, default {}'.format(params.adaptiveThreshWinSizeMin))
    parser.add_argument('--winmax', type=int,
                        default=params.adaptiveThreshWinSizeMax,
                        help='adaptive thresholding window max size, default {}'.format(params.adaptiveThreshWinSizeMax))
    parser.add_argument('--winstep', type=int,
                        default=params.adaptiveThreshWinSizeStep,
                        help='adaptive thresholding window size step , default {}'.format(params.adaptiveThreshWinSizeStep))
    parser.add_argument('--thres', type=float,
                        default=params.adaptiveThreshConstant,
                        help='adaptive threshold constant, default {}'.format(params.adaptiveThreshConstant))
    parser.add_argument('--minrate', type=float,
                        default=params.minMarkerPerimeterRate,
                        help='min marker perimeter rate, default {}'.format(params.minMarkerPerimeterRate))
    parser.add_argument('--maxrate', type=float,
                        default=params.maxMarkerPerimeterRate,
                        help='max marker perimeter rate, default {}'.format(params.maxMarkerPerimeterRate))
    parser.add_argument('--poly', type=float,
                        default=params.polygonalApproxAccuracyRate,
                        help='polygonal approx accuracy rate, default {}'.format(params.polygonalApproxAccuracyRate))
    parser.add_argument('--corner', type=float,
                        default=params.minCornerDistanceRate,
                        help='minimum distance any pair of corners in the same marker, default {}'.format(params.minCornerDistanceRate))
    parser.add_argument('--markerdist', type=float,
                        default=params.minMarkerDistanceRate,
                        help='minimum distance any pair of corners from different markers, default {}'.format(params.minMarkerDistanceRate))
    parser.add_argument('--borderdist', type=int,
                        default=params.minDistanceToBorder,
                        help='minimum distance any marker corner to image border, default {}'.format(params.minDistanceToBorder))
    parser.add_argument('--borderbits', type=int,
                        default=params.markerBorderBits,
                        help='width of marker border, default {}'.format(params.markerBorderBits))
    parser.add_argument('--otsu', type=float, default=params.minOtsuStdDev,
                        help='minimum stddev of pixel values, default {}'.format(params.minOtsuStdDev))
    parser.add_argument('--persp', type=int,
                        default=params.perspectiveRemovePixelPerCell,
                        help='number of pixels per cells, default {}'.format(params.perspectiveRemovePixelPerCell))
    parser.add_argument('--ignore', type=float,
                        default=params.perspectiveRemoveIgnoredMarginPerCell,
                        help='Ignored pixels at cell borders, default {}'.format(params.perspectiveRemoveIgnoredMarginPerCell))
    parser.add_argument('--error', type=float,
                        default=params.maxErroneousBitsInBorderRate,
                        help='Border bits error rate, default {}'.format(params.maxErroneousBitsInBorderRate))
    parser.add_argument('--correct', type=float,
                        default=params.errorCorrectionRate,
                        help='Bit correction rate, default {}'.format(params.errorCorrectionRate))
    parser.add_argument('--refinement', type=int,
                        default=params.cornerRefinementMethod,
                        help='Subpixel process method, default {}'.format(params.cornerRefinementMethod))
    parser.add_argument('--refwin', type=int,
                        default=params.cornerRefinementWinSize,
                        help='Window size for subpixel refinement, default {}'.format(params.cornerRefinementWinSize))
    parser.add_argument('--maxiter', type=int,
                        default=params.cornerRefinementMaxIterations,
                        help='Stop criteria for subpixel process, default {}'.format(params.cornerRefinementMaxIterations))
    parser.add_argument('--minacc', type=float,
                        default=params.cornerRefinementMinAccuracy,
                        help='Stop criteria for subpixel process, default {}'.format(params.cornerRefinementMinAccuracy))
    parser.add_argument('-l', '--list', action="store_true",
                        help='output dictionary names and ids and exit')
    parser.add_argument('--epsg', type=int, default=None,
                        help='epsg code for gcp coordinates, default None')

if __name__ == "__main__":

    # set up command line argument parser
    params = aruco.DetectorParameters_create()
    parser = argparse.ArgumentParser()
    cmd_params(parser, params)
    # parse command line arguments
    args = parser.parse_args()
    gcps = GcpFind(args, params, parser)
    gcps.process_images()

#!/usr/bin/python
#
## @file
#
# Qt Widget for handling the display of camera data.
#
# Hazen 09/13
#

from PyQt4 import QtCore, QtGui

import numpy
import sys

## QCameraWidget
#
# The base class for displaying data from a camera.
#
class QCameraWidget(QtGui.QWidget):
    intensityInfo = QtCore.pyqtSignal(int, int, int)
    mousePress = QtCore.pyqtSignal(int, int)

    ## __init__
    #
    # @param parameters A parameters object.
    # @param parent (Optional) The PyQt parent of this object.
    #
    def __init__(self, parameters, parent = None):
        QtGui.QWidget.__init__(self, parent)
        self.buffer = False
        self.flip_horizontal = parameters.flip_horizontal
        self.flip_vertical = parameters.flip_vertical
        self.image = False
        self.image_min = 0
        self.image_max = 1

        # This is the amount of image magnification.
        # Only integer values are allowed.
        self.magnification = 1

        self.show_grid = False
        self.show_info = True
        self.show_target = False
 
        # This is the x location of the last mouse click.
        self.x_click = 0

        # This is the x size of the image buffer.
        self.x_final = 10

        # This is the x size of the current camera AOI
        # (divided by binning) in pixels.
        self.x_size = 0

        # This the (minimum) x size of the widget. The image from 
        # the camera cannot be rendered smaller than this value.
        self.x_view = 512

        # These are the same as for x.
        self.y_click = 0
        self.y_final = 10
        self.y_size = 0
        self.y_view = 512

    ## blank
    #
    # Initialize the off-screen buffer for image renderin.
    #
    def blank(self):
        painter = QtGui.QPainter(self.buffer)
        color = QtGui.QColor(0, 0, 0)
        painter.setPen(color)
        painter.setBrush(color)
        painter.drawRect(0, 0, self.width(), self.height())

    ## calcFinalSize
    #
    # "Final" is the size at which to draw the pixmap that will actually 
    # be shown in the window.
    #
    # Based on the final size, determine the best size for a square window. 
    # Set the widget size to this & create a buffer of this size. We'll
    # draw in the buffer first, then copy to the window.
    #
    def calcFinalSize(self):

        self.x_final = self.x_view
        self.y_final = self.y_view
        if (self.x_size > self.y_size):
            self.y_final = self.x_view * self.y_size / self.x_size
        elif (self.x_size < self.y_size):
            self.x_final = self.y_view * self.x_size / self.y_size

        self.x_final = self.x_final * self.magnification
        self.y_final = self.y_final * self.magnification

        w_size = self.x_final
        if (self.y_final > self.x_final):
            w_size = self.y_final

        self.setFixedSize(w_size, w_size)
        self.buffer = QtGui.QPixmap(w_size, w_size)

        self.blank()

    ## getAutoScale
    #
    # This returns the minimum and maximum values to use for automatically
    # re-scaling the image based on the most recent camera data.
    #
    # @return [camera data value to use as zero, camera data value to use as 255]
    #
    def getAutoScale(self):
        margin = int(0.1 * float(self.image_max - self.image_min))
        return [self.image_min - margin, self.image_max + margin]

    ## mousePressEvent
    #
    # Convert the mouse click location into camera pixels. The xy 
    # coordinates of the event are correctly adjusted for the scroll 
    # bar position, we just need to scale them correctly. This causes
    # a mousePress event to be emitted.
    #
    # @param event A PyQt mouse press event.
    #
    def mousePressEvent(self, event):
        self.x_click = event.x() * self.x_size / self.x_final
        self.y_click = event.y() * self.y_size / self.y_final

        if (self.x_click >= self.x_size):
            self.x_click = self.x_size - 1
        if (self.y_click >= self.y_size):
            self.y_click = self.y_size - 1

        self.mousePress.emit(self.x_click, self.y_click)

    ## newColorTable
    #
    # Note that the color table of the image that is being displayed 
    # will not actually change until updateImageWithFrame() is called.
    #
    # @param colortable A python array of color table values.
    #
    def newColorTable(self, colortable):
        self.colortable = colortable

    ## newParameters
    #
    # @param parameters A parameters object.
    # @param colortable A color table Python array.
    # @param display_range [minimum, maximum]
    #
    def newParameters(self, parameters, colortable, display_range):
        self.colortable = colortable
        self.display_range = display_range
        self.flip_horizontal = parameters.flip_horizontal
        self.flip_vertical = parameters.flip_vertical
        self.rotate90 = parameters.rotate90
        self.x_size = parameters.x_pixels/parameters.x_bin
        self.y_size = parameters.y_pixels/parameters.y_bin

        self.calcFinalSize()

    ## newRange
    #
    # @param range [minimum, maximum]
    #
    def newRange(self, range):
        self.display_range = range

    ## paintEvent
    #
    # self.image is the image from the camera scaled to the buffer
    #    size.
    #
    # self.buffer is where the image is temporarily re-drawn prior 
    #    to final display. In theory this reduces display flickering.
    #
    # @param event A PyQt paint event.
    #
    def paintEvent(self, event):
        if self.image:
            painter = QtGui.QPainter(self.buffer)

            # Draw current image into the buffer, appropriately scaled.
            # Only draw what is actually visible.
            vr = self.visibleRegion().boundingRect()
            painter.drawImage(vr, self.image, vr)

            # Draw the grid into the buffer.
            if self.show_grid:
                x_step = self.width()/8
                y_step = self.height()/8
                painter.setPen(QtGui.QColor(255, 255, 255))
                for i in range(7):
                    painter.drawLine((i+1)*x_step, 0, (i+1)*x_step, self.height())
                    painter.drawLine(0, (i+1)*y_step, self.width(), (i+1)*y_step)

            # Draw the target into the buffer
            if self.show_target:
                mid_x = self.width()/2 - 20
                mid_y = self.height()/2 - 20
                painter.setPen(QtGui.QColor(255, 255, 255))
                painter.drawEllipse(mid_x, mid_y, 40, 40)

            # Transfer the buffer to the screen.
            painter = QtGui.QPainter(self)
            painter.drawPixmap(0, 0, self.buffer)

    ## setColorTable
    #
    # Changes the color table of the current image.
    #
    def setColorTable(self):
        if self.colortable:
            for i in range(256):
                self.image.setColor(i, QtGui.qRgb(self.colortable[i][0], 
                                                  self.colortable[i][1], 
                                                  self.colortable[i][2]))
        else:
            for i in range(256):
                self.image.setColor(i,QtGui.qRgb(i,i,i))

    ## setMagnification
    #
    # Note that the magnification of the image that is being displayed 
    # will not actually change until updateImageWithFrame() is called.
    #
    # @param new_magnification The new magnification factor, an integer > 0.
    #
    def setMagnification(self, new_magnification):
        self.magnification = new_magnification
        self.calcFinalSize()

    ## setShowGrid
    #
    # @param bool True/False Overlay a grid on the image from the camera.
    #
    def setShowGrid(self, bool):
        if bool:
            self.show_grid = True
        else:
            self.show_grid = False

    ## setShowInfo
    #
    # @param bool True/False Display intensity information for the last pixel that was clicked on.
    #
    def setShowInfo(self, bool):
        if bool:
            self.show_info = True
        else:
            self.show_info = False

    ## setShowTarget
    #
    # @param bool True/False Overlay a circle in the center of the image from the camera.
    #
    def setShowTarget(self, bool):
        if bool:
            self.show_target = True
        else:
            self.show_target = False

    ## updateImageWithFrame
    #
    # This takes the image from the camera, scales it, resizes it and converts it
    # into a QImage that can be drawn in the display. It also emits the intensityInfo
    # signal with the current intensity of the pixel of interest.
    #
    # @param frame A frame object.
    #
    def updateImageWithFrame(self, frame):
        if frame:
            w = frame.image_x
            h = frame.image_y
            image_data = frame.getData()
            image_data = image_data.reshape((h,w))
            self.image_min = numpy.min(image_data)
            self.image_max = numpy.max(image_data)

            if self.flip_horizontal:
                image_data = numpy.fliplr(image_data)

            if self.flip_vertical:
                image_data = numpy.flipud(image_data)

            if self.rotate90:
                image_data = numpy.rot90(image_data)

            temp = image_data.astype(numpy.float32)
            temp = 255.0*(temp - self.display_range[0])/(self.display_range[1] - self.display_range[0])
            temp[(temp > 255.0)] = 255.0
            temp[(temp < 0.0)] = 0.0
            temp = temp.astype(numpy.uint8)

            # Create QImage & draw at final magnification.
            temp_image = QtGui.QImage(temp.data, w, h, QtGui.QImage.Format_Indexed8)
            self.image = temp_image.scaled(self.x_final, self.y_final)
            self.image.ndarray = temp

            # Set the images color table.
            self.setColorTable()
            self.update()

            if self.show_info:
                x_loc = self.x_click
                y_loc = self.y_click
                value = 0
                if ((x_loc >= 0) and (x_loc < w) and (y_loc >= 0) and (y_loc < h)):
                    value = image_data[y_loc, x_loc]
                    self.intensityInfo.emit(x_loc, y_loc, value)

#    #
#    # This is called after initialization to get the correct 
#    # default size based on the size of the scroll area as 
#    # specified using QtDesigner.
#    #
#    def updateSize(self):
#        self.x_final = self.width()
#        self.x_view = self.width()
#        self.y_final = self.height()
#        self.y_view = self.height()

#    def wheelEvent(self, event):
#        if (event.delta() > 0):
#            self.magnification += 1
#        else:
#            self.magnification -= 1
#        
#        if (self.magnification < 1):
#            self.magnification = 1
#        if (self.magnification > 8):
#            self.magnification = 8
#
#        self.calcFinalSize()


#
# Testing
#

if __name__ == "__main__":
    class Parameters:
        def __init__(self):
            self.x_pixels = 200
            self.y_pixels = 200

    parameters = Parameters()
    app = QtGui.QApplication(sys.argv)
    viewer = QCameraWidget(parameters, [200,400])
    viewer.show()

    sys.exit(app.exec_())


#
# The MIT License
#
# Copyright (c) 2013 Zhuang Lab, Harvard University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

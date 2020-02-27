import numpy as np
import matplotlib.pyplot as plt
import sys
from PIL import Image
from queue import Queue

class Floodfill:

	def __init__(self, source, name = None):
		if type(source) == str:
			if source.lower().endswith('.png'):
				png_data = np.array(Image.open(source))

				plt.figure(figsize=(50,50))
				plt.imshow(png_data[:,15000:15250], cmap='inferno')
				plt.show()

				flooded_png = Floodfill.flood_iterative(png_data[:,15000:15250], (0,0), 255, 0, 15)

				plt.figure(figsize=(50,50))
				plt.imshow(png_data[:15000:15250], cmap='inferno')
				plt.show()

	
	def within_threshold(x, target_color, threshold):
		"""
		within_threshold checks whether cell is within the target_color 
		and the specified threshold bands
		"""
		return x >= (target_color - threshold) or x <= (target_color + threshold)

	def flood_iterative(image, xy, target_color, replacement_color, threshold):
		x = xy[0]
		y = xy[1]

		print(image.shape)

		if target_color == replacement_color:
			return
		elif not Floodfill.within_threshold(image[x,y], target_color, threshold):
			return	
		else:
			image[x,y] = replacement_color
			q = Queue()
			q.put(xy)
			while not q.empty():
				xy = q.get()
				print(xy)
				x = xy[0]
				y = xy[1]
				if x+1 < image.shape[0] and Floodfill.within_threshold(image[x+1,y], target_color, threshold):
					image[x+1,y] = replacement_color
					q.put([x+1,y])
				if x-1 >= 0 and Floodfill.within_threshold(image[x-1,y], target_color, threshold):
					image[x-1,y] = replacement_color
					q.put([x-1,y])
				if y-1 >= 0 and Floodfill.within_threshold(image[x,y-1], target_color, threshold):
					image[x,y-1] = replacement_color
					q.put([x,y-1])
				if y+1 < image.shape[0] and Floodfill.within_threshold(image[x,y+1], target_color, threshold):
					image[x,y+1] = replacement_color
					q.put([x,y+1])


	def flood(image, xy, target_color, replacement_color, threshold):
		"""
		flood performs a flood-fill operation on the specified start location in 
		the given image, replacing the target_color cells with replacement_color 
		cells and spreads to neighboring cells based on the specified threshold.
		"""
		print('image shape: ', image.shape)

		x = xy[0]
		y = xy[1]
		
		#print(image[:,0:1])

		# if the target color is equal to replacement_color, return
		# else if the color of node is not equal to target_color, return
		# else set the color of node to replacement_color
		# recurse flood() on neighboring pixels
		
		if target_color == replacement_color:
			return
		elif x < 0 or x >= image.shape[0] or y < 0 or y >= image.shape[1]:
			return
		elif Floodfill.within_threshold(image[x, y], target_color, threshold):
			image[x, y] = replacement_color
			Floodfill.flood(image, (x+1,y), target_color, replacement_color, threshold)	
			Floodfill.flood(image, (x-1,y), target_color, replacement_color, threshold)	
			Floodfill.flood(image, (x,y+1), target_color, replacement_color, threshold)	
			Floodfill.flood(image, (x,y-1), target_color, replacement_color, threshold)	
		else:
			return

	def write_to_png(image):
		print('writing to PNG')

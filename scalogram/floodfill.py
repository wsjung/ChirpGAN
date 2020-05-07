import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import sys
# from PIL import Image
from queue import Queue

import gc


class Floodfill:

	def __init__(self, source, name = None):
		if type(source) == str:
			if source.lower().endswith('.png'):
				self.name = source[:-4]
				# img = Image.open(source)
				# tmp = np.array(img)

				# display image
				"""
				f = plt.figure(figsize=(10,10))
				plt.imshow(tmp, cmap='inferno')
				plt.show()
				"""
				#f.savefig('./floodfill_testruns/orig.png', bbox_inches='tight')
				# img.save('./floodfill_testruns/orig.png')
				#img.close()
				#plt.close(f)


				# bucket fill threshold range
				for threshold in range(10,11):
					# img = Image.open(source)
					img = mpimg.imread(source)
					png_data = np.array(img)
					# img.close()
					# gc.collect()

					print(png_data.shape)


					print("image loaded")

					print('### Testing threshold = %d ###' % threshold, flush=True)

					# self.png_data = png_data

					flooded_png = self.flood_iterative(png_data, xy=(50,50), target_color=0, replacement_color=255, threshold=threshold)
					self.png_data = flooded_png

					print('self.png_data.shape: ', self.png_data.shape)

					print("image flooded")

					#print(flooded_png)
					#print(flooded_png.dtype)


					# save bucket filled image
					# fig = plt.figure(figsize=(10,10))
					# plt.imshow(flooded_png, cmap='inferno')
					# print('saving file..', end='', flush=True)
					#fig.savefig('./z_floodfill_testruns/8d_test_threshold_%d.png' % threshold, bbox_inches='tight', format='png')
					#fig.savefig('./floodfill_testruns/8d_test_threshold_%d.png' % threshold, bbox_inches='tight', format='png')

					# im = Image.fromarray(flooded_png)
					# im.save('./floodfill_testruns/8d_test_threshold_%d.png' % threshold)

					# print('.', flush=True)


					# close figure and image
					# plt.close(fig)
					# img.close()


	def within_threshold(self, x, target, threshold):
		"""
		within_threshold checks whether cell is within the target_color 
		and the specified threshold bands
		"""
		return x > (target - threshold) and x < (target + threshold)

	def within_image(self, x, y, shape):
		return x >= 0 and x < shape[0] and y >= 0 and y < shape[1]


	def flood_iterative(self, image, xy, target_color, replacement_color, threshold):
		"""
		Args:
			image (np.array): image 
			xy (tuple (x,y)): starting location 
			target_color (int): the color we want replaced
			replacement_color (int): the color we want replaced into
			threshold (int): the threshold for classifying a color as target_color
		"""
		x = xy[0]
		y = xy[1]


		print('image shape: ', image.shape)

		if target_color == replacement_color:	# already the specified replacement_color 
			print('replacement color is already target color')
			return
		elif not self.within_threshold(image[x,y], target_color, threshold):	# not the target color we want
			print('not the target color we want')
			return	
		else:
			init_target_color = image[x,y]	# set initial target color
			print('init_target_color: %d' % init_target_color)

			sq = SetQueue()	# queue for future locations
			sq.put(xy)

			# i = 0
			while not sq.empty():
				# i+=1

				loc = sq.get()	# get next location
				x = loc[0]
				y = loc[1]
				loc = None
				gc.collect()
				
				if self.within_image(x, y, image.shape):
					if self.within_threshold(image[x,y], init_target_color, threshold):	# replace color if within target threshold
						image[x,y] = replacement_color
				
					# add neighbors to the queue
					sq.put((x+1,y))
					# sq.put((x+1,y+1))
					# sq.put((x+1,y-1))
					sq.put((x-1,y))
					# sq.put((x-1,y+1))
					# sq.put((x-1,y-1))
					sq.put((x,y+1))
					sq.put((x,y-1))
			
			# print('FINISHED WITH WHILE LOOP\ni=%d' % i)
		

		# self.png_data = image
		
		print("image flooded")
		return image


	def flood(self, image, xy, target_color, replacement_color, threshold):
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
		elif self.within_threshold(image[x, y], target_color, threshold):
			image[x, y] = replacement_color
			self.flood(image, (x+1,y), target_color, replacement_color, threshold)	
			self.flood(image, (x-1,y), target_color, replacement_color, threshold)	
			self.flood(image, (x,y+1), target_color, replacement_color, threshold)	
			self.flood(image, (x,y-1), target_color, replacement_color, threshold)	
		else:
			return

	def write_to_png(self, filename=None):
		# from scipy.misc import toimage
		# print('writing to PNG')

		# if filename == None: filename == self.name + "_flooded.png"

		# im = toimage(self.png_data)
		# im.save(filename)
		# im.close()
		print('writing to PNG')
		if filename == None: filename == self.name + "_flooded.png"
		
		import png
		png.from_array(self.png_data, mode='L').save(filename)

		

class SetQueue:

	def put(self, item):
		if item not in self.setqueue_set:
			self.setqueue_set.add(item)
			self.setqueue_queue.put(item)
			self.size += 1

	def get(self):
		item = self.setqueue_queue.get()
		#self.setqueue_set.remove(item)
		self.size -= 1
		return item

	def empty(self):
		return self.size==0

	def __init__(self):
		self.setqueue_set = set()
		self.setqueue_queue = Queue()
		self.size = 0
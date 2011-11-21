# Evan Bollig, Gordon Erlebacher, Ian Johnson
# Department of Scientific Computing
# Florida State University
# April, 2010
# 
# Render all cameras for current frame before proceeding to the next frame
# 
# To use: 
# 	1 - Set the blender units scale here. This will scale the eye separation 
#		to acurately represent a human pair in the blender environment
#		examples: 
#			 bu = 0.1 # 1 b.u. = 1 mm
#			 bu = 100 # 1 b.u. = 1 m 

bu = 0.1 # 1 b.u. = 1 cm

#	2 - Load this script in a Blender Text Editor Area
# 	3 - Hit ALT + P to execute script
# 	4 - Watch in amazement as a stereo snapshot is rendered from the view of each camera
#	5 - Find the output image sequence in the directory specified by the Scene tab in the Buttons
#		Window (Shortcut F10). 
#		For example: I set output dir to be "/tmp" and have a single camera in my 
#		scene (called "Camera"). My output frames go to:
#			"/tmp/Camera/Camera_SLEFT/Camera_SLEFT.*.png" and 
#			"/tmp/Camera/Camera_SRIGHT/Camera_SRIGHT.*.png"
#	6 - To prematurely interrupt the animation process, press CTRL-C in the terminal. 
#		(WARNING! if you do not run Blender in a terminal and launch this script, there is no 
#				way to interrupt the process!)
#############################################################################################
from Blender import Camera, Object, Scene, Mesh, Window
import copy
import math

class StereoAnimator:
	##########################################
	# Class Member Data ([Type] [name]):
	#
	# Blender.Scene scene	// The scene containing cameras which will be rigged stereo
	# 
	# Blender.RenderingContext context // the scene rendering context
	# 
	# List[List] rig_cams	// A list of stereo camera rigs [type List[Object("Camera") Object("Camera")]
	#							(Tuple is combo: [rig camera, original camera])
	#
	# List rig_cams_data	// A list of camera data associated with rig_cams
	#
	# Blender.Camera orig_cam 	// The original active camera of scene
	# 
	# Integer orig_frame	// The original active frame of scene
	##########################################
	
	def __init__(self, scene_, defaultEyeSeparation):
		# Assume each camera is independent. Then, we parent a Stereo_LEFT and 
		# Stereo_RIGHT camera to each camera
		# At the end of the animation we will delete all of the cameras in the
		# rig_cams list. 
		#
		# This is a queue of cameras we will render from 
		self.rigs = []
		self.rig_cams_data = []

		self.scene = scene_
		
		self.BackupScene()
		self.PrintCameraData()
		self.PrintSceneCameras()
		
		self.eyeSep = defaultEyeSeparation
	
	# Return a list of cameras in the scene
	# RETURN: the list of cameras
	def GetCameraList(self, blender_scene): 
		cams= [ob for ob in blender_scene.objects if ob.getType()=='Camera']
		return cams
	
	# Checkpoint the scene so any modifications we make can be undone
	# RETURN: nothing
	def BackupScene(self):
		# backup the active cam.
		self.orig_cam = self.scene.objects.camera
		self.context = self.scene.getRenderingContext()
		self.orig_frame = self.context.currentFrame()
		self.output_path_orig = self.context.getRenderPath()
	
	# print all camera DATA
	# (IS THIS ONLY IN THE CURRENT SCENE OR GLOBAL?)
	# RETURN: nothing
	def PrintCameraData(self):
		cam_data = [c.getName() for i, c in enumerate(Camera.Get())]
		print "CAMERA DATA IN SCENE: ", ", ".join(cam_data), "\n"
	
	# print all camera objects in scene
	# RETURN: nothing
	def PrintSceneCameras(self):
		for i, c in enumerate(self.GetCameraList(self.scene)):
			print "CAMERA OBJECTS IN SCENE: " + c.getName(), "\n"

	# print all cameras in the Blender environment
	def PrintAllBlenderCameras(self):
		cams = [ob.getName() for ob in Object.Get() if ob.getType() == 'Camera']
		print "ALL CAMS IN BLENDER: ", ", ".join(cams)

	# Print the stereo camera rig names
	def PrintStereoRigs(self):
		print "\nSTEREO RIG CAMERAS:"
		print self.rigs
		for indx, [[l,r],s,o] in enumerate(self.rigs):
			print indx, "\t",o.getName(), " ->  *", l.getName(), r.getName()
		print ""
	

	# Copy a single attribute (attr) from the src to the dest object
	def CopyAttribute(self, attr, dest, src):
		try:  
			setattr(dest, attr, getattr(src, attr))
		#	print "COPIED ", attr
		except: 
		#	print "ATTRIBUTE: ", attr, " NOT FOUND"
			pass
		
	def UpdateRig(self, leftCam, rightCam, eyeSeperator, origCam):
		self.UpdateCameraObject(leftCam, origCam)
		self.UpdateCameraObject(rightCam,origCam)
		
		self.CopyRotLoc(eyeSeperator, origCam)
		
		locs = self.GetEndpointLocations(eyeSeperator)
			
		self.ApplyLoc(leftCam, locs[0])
		self.ApplyLoc(rightCam, locs[1])	

		# For shiftx calculation: 
		render_width = self.context.imageSizeX()
		print "WIDTH: ", render_width
		cam_separation = self.eyeSep
		print "EyeSep: ", cam_separation
		focal_dist = origCam.getData().dofDist
		if (focal_dist == 0): 
			print "\n!!!!! WARNING !!!!! focal dist is 0. Cameras will be parallel with no convergence! Select each camera, go to Edit Tab (F9) and set Dof Dist to fix this! (No support for Dof Ob yet)\n"
			leftCam.getData().shiftX = 0
			rightCam.getData().shiftX = 0
		else: 
			print "DOF: ", focal_dist
			# From http://www.noeol.de/s3d/BStereoOffAxisCamera_0_4.py
			camera_fov = math.radians(origCam.getData().angle / 2.)
			#camera_fov = origCam.getData().angle / 2.
			print "FOV: ", camera_fov

			# Next two lines from http://www.noeol.de/s3d/BStereoOffAxisCamera_0_5_2.py
			# calculate delta (in pixel)
			delta = (render_width*cam_separation)/(2.*focal_dist*math.tan(camera_fov))
			camera_shift_x = delta/render_width
			
			# ShiftX adjustment for parallel stereo
			leftCam.getData().shiftX = (camera_shift_x/2.)
			rightCam.getData().shiftX = -(camera_shift_x/2.)
			
			print "SHIFTX ", camera_shift_x/2., camera_shift_x	
		
	# Update attributes of destination camera based on source camera
	def UpdateCameraObject(self, dest, src): 
		# List of candidates (for reference only)...
		# As of Blender 2.49b (04/20/2010):
		# ['DupEnd', 'DupGroup', 'DupObjects', 'DupOff', 'DupOn', 'DupSta', 
		#	'Layer', 'Layers', 'LocX', 'LocY', 'LocZ', 'RotX', 'RotY', 
		#	'RotZ', 'SizeX', 'SizeY', 'SizeZ', '__class__', '__cmp__', 
		#	'__copy__', '__delattr__', '__doc__', '__getattribute__', 
		#	'__hash__', '__init__', '__new__', '__reduce__', '__reduce_ex__', 
		#	'__repr__', '__setattr__', '__str__', 'action', 'actionStrips', 
		#	'activeMaterial', 'activeShape', 'addProperty', 'addScriptLink', 
		#	'addVertexGroupsFromArmature', 'axis', 'boundingBox', 'buildParts',
		#	'clearIpo', 'clearScriptLinks', 'clearTrack', 'clrParent', 'colbits',
		#	'color', 'constraints', 'convertActionToStrip', 'copy', 
		#	'copyAllPropertiesTo', 'copyNLA', 'dLocX', 'dLocY', 'dLocZ', 'dRotX', 
		#	'dRotY', 'dRotZ', 'dSizeX', 'dSizeY', 'dSizeZ', 'data', 'dloc', 
		#	'drawMode', 'drawSize', 'drawType', 'drot', 'dsize', 'dupFacesScaleFac', 
		#	'effects', 'emptyShape', 'enableDupFaces', 'enableDupFacesScale', 
		#	'enableDupFrames', 'enableDupGroup', 'enableDupNoSpeed', 'enableDupRot',
		#	'enableDupVerts', 'enableNLAOverride', 'evaluatePose', 'fakeUser', 
		#	'game_properties', 'getAction', 'getAllProperties', 'getBoundBox', 
		#	'getData', 'getDeltaLocation', 'getDrawMode', 'getDrawType', 'getEuler', 
		#	'getInverseMatrix', 'getIpo', 'getLocation', 'getMaterials', 'getMatrix', 
		#	'getName', 'getPIDeflection', 'getPIFalloff', 'getPIMaxDist', 'getPIPerm', 
		#	'getPIRandomDamp', 'getPIStrength', 'getPISurfaceDamp', 'getPIType', 
		#	'getPIUseMaxDist', 'getParent', 'getParentBoneName', 'getParticleSystems', 
		#	'getPose', 'getProperty', 'getSBDefaultGoal', 'getSBErrorLimit', 
		#	'getSBFriction', 'getSBGoalFriction', 'getSBGoalSpring', 'getSBGravity', 
		#	'getSBInnerSpring', 'getSBInnerSpringFriction', 'getSBMass', 'getSBMaxGoal', 
		#	'getSBMinGoal', 'getSBStiffQuads', 'getSBUseEdges', 'getSBUseGoal', 
		#	'getScriptLinks', 'getSize', 'getTimeOffset', 'getTracked', 'getType', 
		#	'insertCurrentPoseKey', 'insertIpoKey', 'insertPoseKey', 'insertShapeKey', 
		#	'ipo', 'isSB', 'isSelected', 'isSoftBody', 'join', 'layers', 'lib', 'link', 
		#	'loc', 'makeDisplayList', 'makeParent', 'makeParentBone', 'makeParentDeform', 
		#	'makeParentVertex', 'makeTrack', 'mat', 'materialUsage', 'matrix', 
		#	'matrixLocal', 'matrixOldWorld', 'matrixParentInverse', 'matrixWorld', 
		#	'modifiers', 'name', 'nameMode', 'newParticleSystem', 'parent', 'parentType', 
		#	'parentVertexIndex', 'parentbonename', 'passIndex', 'piDeflection', 
		#	'piFalloff', 'piMaxDist', 'piPermeability', 'piRandomDamp', 'piSoftbodyDamp', 
		#	'piSoftbodyIThick', 'piSoftbodyOThick', 'piStrength', 'piSurfaceDamp', 
		#	'piType', 'piUseMaxDist', 'pinShape', 'properties', 'protectFlags', 'rbFlags', 
		#	'rbHalfExtents', 'rbMass', 'rbRadius', 'rbShapeBoundType', 'removeAllProperties',
		#	'removeProperty', 'restrictDisplay', 'restrictRender', 'restrictSelect', 'rot', 
		#	'sbDefaultGoal', 'sbErrorLimit', 'sbFriction', 'sbGoalFriction', 'sbGoalSpring', 
		#	'sbGrav', 'sbInnerSpring', 'sbInnerSpringFrict', 'sbMass', 'sbMaxGoal', 'sbMinGoal',
		#	'sbSpeed', 'sbStiffQuads', 'sbUseEdges', 'sbUseGoal', 'sel', 'select', 
		#	'setConstraintInfluenceForBone', 'setDeltaLocation', 'setDrawMode', 'setDrawType',
		#	'setEuler', 'setIpo', 'setLocation', 'setMaterials', 'setMatrix', 'setName', 
		#	'setPIDeflection', 'setPIFalloff', 'setPIMaxDist', 'setPIPerm', 'setPIRandomDamp',
		#	'setPIStrength', 'setPISurfaceDamp', 'setPIType', 'setPIUseMaxDist', 
		#	'setSBDefaultGoal', 'setSBErrorLimit', 'setSBFriction', 'setSBGoalFriction', 
		#	'setSBGoalSpring', 'setSBGravity', 'setSBInnerSpring', 'setSBInnerSpringFriction', 
		#	'setSBMass', 'setSBMaxGoal', 'setSBMinGoal', 'setSBStiffQuads', 'setSBUseEdges', 
		#	'setSBUseGoal', 'setSize', 'setTimeOffset', 'shareFrom', 'size', 'tag', 'texSpace',
		#	'timeOffset', 'track', 'trackAxis', 'transp', 'type', 'upAxis', 'users', 
		#	'wireMode', 'xRay']
		
		# TODO: reduce this set to essential fields only
		copyable_attr = ['Layer', 'Layers', 'LocX', 'LocY', 'LocZ', 'RotX', 'RotY','RotZ', 'SizeX', 'SizeY', 'SizeZ','dLocX', 'dLocY', 'dLocZ', 'dRotX', 'dRotY', 'dRotZ', 'dSizeX', 'dSizeY', 'dSizeZ', 'dloc','drot', 'dsize', 'game_properties', 'layers', 'loc', 'mat', 'matrix', 'matrixLocal', 'matrixOldWorld', 'matrixParentInverse', 'matrixWorld', 'modifiers','parent','properties', 'rot', 'size', 'tag', 'texSpace','timeOffset', 'track', 'trackAxis', 'transp', 'type', 'upAxis','wireMode', 'xRay']
		
		#print "Trying to copy: ", ",".join(copyable_attr)
		for attr in copyable_attr:
			self.CopyAttribute(attr, dest, src)
		print "Copied camera attributes manually"
	
	def UpdateCameraData(self, dest, src):
		# List of candidates (for reference only)...
		# As of Blender 2.49b (04/20/2010):
		# ['__class__', '__cmp__', '__copy__', '__delattr__', '__doc__',
		#  '__getattribute__', '__hash__', '__init__', '__new__', 
		#  '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', 
		#  '__str__', 'addScriptLink', 'alpha', 'angle', 'angleToggle', 
		#  'clearIpo', 'clearScriptLinks', 'clipEnd', 'clipStart', 
		#  'copy', 'dofDist', 'drawLimits', 'drawMist', 'drawName', 
		#  'drawPassepartout', 'drawSize', 'drawTileSafe', 'fakeUser', 
		#  'getClipEnd', 'getClipStart', 'getDrawSize', 'getIpo', 
		#  'getLens', 'getMode', 'getName', 'getScale', 'getScriptLinks', 
		#  'getType', 'insertIpoKey', 'ipo', 'lens', 'lib', 'mode', 
		#  'name', 'properties', 'scale', 'setClipEnd', 'setClipStart', 
		#  'setDrawSize', 'setIpo', 'setLens', 'setMode', 'setName', 
		#  'setScale', 'setType', 'shiftX', 'shiftY', 'tag', 'type', 
		#  'users']
		#print "NO CAMERA DATA ATTRIBUTES TO COPY"
		copyable_attr = ['alpha', 'angle','clipEnd', 'clipStart','dofDist','drawLimits', 'drawMist', 'drawName','drawPassepartout', 'drawSize', 'drawTileSafe','lens','mode','scale','shiftX', 'shiftY']
		for attr in copyable_attr:
			self.CopyAttribute(attr, dest, src)
		print "Copied cameraData attributes manually"	

	# Create new camera as copy of original
	# with the name [originalCameraName]+[name_suffix]
	# RETURN: tuple [cloned camera, cloned camera data]
	def CloneCamera(self, camera, name_suffix):
		
		dataName = camera.getName() + "_DATA" + name_suffix
		objectName = camera.getName() + name_suffix
	
		# NOTE: this try: except: may not be needed. If the cameraObject
		#	below is a copy of the original camera, then its cameraData
		#	is not what we recover or construct here. 
		try:
			# try to recover existing camera and camera data objects
			# if these throw an exception its because the names do not 
			# exist and we need to create the first instance
			print "Looking for data: ", dataName
			cameraData = Camera.Get(dataName)
			#print "------- OLD: ", cameraData
			#cameraData.copy(camera.getData())				
			#print "------- NEW: ", cameraData
			#self.UpdateCameraData(cameraData, camera.getData())
			print "Got data"
		except: 
			# NO DATA exists (CONSTRUCT IT)
			# cameraData = camera.copy() #copy.copy(camera.getData()) #Camera.New("persp")
			cameraData = camera.getData().copy()
			# try to match the camera data and camera object names
			cameraData.name = dataName
			print "+++++ CONSTRUCTED CAMERA DATA"
	
		# NOTE: If we copy the camera Object below rather than construct a new 
		# 		camera, then the copy links to the original camera data. 
		# 		Presumably this is fine. Since stereo rigs should have the same
		#		focal distance, lense size, etc as the original camera. 
		#		We should consider removing the dependency on recovering the 
		#		camera data above. I left it in there now because it adds very
		# 		little computation but is a huge life saver if somethign is 
		#		wrong. 
		# NOTE: In fact, I can use the shiftX to make the stereo 
		# 	"Asymmetric Frustrum Parallel Axis Projection Stereo"
		# 	(see: http://www.orthostereo.com/geometryopengl.html)
		try:
			print "Looking for object: ", objectName
			cameraObject = Object.Get(objectName)
			print "Got object"
			#cameraObject.setName(objectName)
			self.scene.objects.link(cameraObject)
			print "+++++ RELINKED", objectName
		except: 
			# Copy.copy will create a new object, but it will have 
			# all the settings of the original camera. Also, it is NOT
			# linked to the scene by default
			#print "BEFOR COPY"
			#self.PrintAllBlenderCameras()
			#EB cameraObject = copy.copy(camera) 
			#EB cameraObject.setName(objectName)
			#print "AFTER COPY"
			#self.PrintAllBlenderCameras()
			#print "BEFORE LINK"
			#self.PrintSceneCameras()
			#EB self.scene.objects.link(cameraObject)
			#print "AFTER LINK"
			#self.PrintSceneCameras()
			#EB print "++++++ COPIED CAMERA OBJECT"
			##### ALTERNATIVE (COMMENT ALL ABOVE (Up to but excluding "except:") TO USE) #####
			# this automatically links the camera object into the scene
			cameraObject = self.scene.objects.new(cameraData)
			cameraObject.setName(objectName)
			print "+++++ CONSTRUCTED Camera", cameraObject
		
		# Good, I dont need to recapture the cameraData object in the try-catch 
		# above. If I clone the camera object the cameraData belongs to the 
		# original camera. I only need this to get the dept of field (dofDist) 
		# property so I can the crop sizes on the cameras using a parameter 
		# camera separation!
		cameraData = cameraObject.getData()
		
		print "CameraData \'", cameraData.name, "\' DoF: ", cameraData.dofDist, "\t", cameraObject.getData().dofDist
		
		# TODO: copy all setting of orginal camera into clone
		return [cameraObject, cameraData]
	
	# Copy the rotation and location from a src object to a dest object
	def CopyRotLoc(self, dest, src):	
		dest.LocX = src.LocX
		dest.LocY = src.LocY
		dest.LocZ = src.LocZ
		dest.RotX = src.RotX
		dest.RotY = src.RotY
		dest.RotZ = src.RotZ
		dest.getData().update()
	
	# Copy the rotation from a src object to a dest object
	def CopyRot(self, dest, src):	
		dest.RotX = src.RotX
		dest.RotY = src.RotY
		dest.RotZ = src.RotZ
	# Not available in CameraData
	#	dest.getData().update()
	
	# Set the location of a dest object to match an XYZ vector
	def ApplyLoc(self, dest, locVector):
		dest.LocX = locVector[0]
		dest.LocY = locVector[1]
		dest.LocZ = locVector[2]
	
	
	# from http://en.wikibooks.org/wiki/Blender_3D:_Blending_Into_Python/Cookbook
	# Transform a vertex into global coordinates
	def apply_transform(self, vec, matrix):
		x, y, z = vec
		xloc, yloc, zloc = matrix[3][0], matrix[3][1], matrix[3][2]
		return	x*matrix[0][0] + y*matrix[1][0] + z*matrix[2][0] + xloc,\
				x*matrix[0][1] + y*matrix[1][1] + z*matrix[2][1] + yloc,\
				x*matrix[0][2] + y*matrix[1][2] + z*matrix[2][2] + zloc

	# Get the global coordinates of the segment endpoints [(left), (right)]
	def GetEndpointLocations(self, segmentObject):
		locations = []
		for vert in [segmentObject.getData().verts]:
			for v in vert:
				locations += [self.apply_transform(v, segmentObject.getMatrix())]
		return locations
	
	# Create a line segment that can be positioned to match the original camera
	# but with endpoints that will be the locations of our stereo rig cameras
	def CreateSegment(self, camera, nameSuffix, length): 
		editmode = Window.EditMode()    # are we in edit mode?  If so ...
		if editmode: Window.EditMode(0) # leave edit mode before getting the mesh
		
		name = camera.getName() + nameSuffix
		
		# define vertices and faces for a pyramid
		coords=[ [-length/2,0,0], [length/2,0,0] ]  
		edges=[ [0, 1] ] 
		
		try: 
			print "LOOKING FOR MESHDATA"
			me = Mesh.Get(name + 'mesh')
			print dir(me)
		except:
			print "COULD NOT FIND MESH" 
			me = Mesh.New(name + 'mesh')
		
		#print "____ EDGES: ", len(me.edges), "____ VERTS: ", len(me.verts)
		
		me.verts = None
		me.edges.delete()
		
		#print "____ EDGES: ", len(me.edges), "____ VERTS: ", len(me.verts)
						
		me.verts.extend(coords)          # add vertices to mesh
		me.edges.extend(edges)           # add faces to the mesh (also adds edges)
		
		#print "____ EDGES: ", len(me.edges), "____ VERTS: ", len(me.verts)
		try: 
			print "TRYING TO RECOVER OBJECT: "
			ob = Object.Get(name)
			print "++++++ OBJECT RECOVERED: "
		except: 
			print "++++++ CREATING NEW OBJECT"
			ob = self.scene.objects.new(me, name)
		
		if editmode: Window.EditMode(1)  # optional, just being nice
			
		return ob
	
	
	# Create the stereo rigs:
	# 	- A left and right camera for each camera passed into function
	# 	- Name of each camera will be [originalName]+["_SLEFT"|"_SRIGHT"] 	
	def GenerateStereoRigs(self, eyeSeparation):
		for i, c in enumerate(self.GetCameraList(self.scene)):	
			[cameraLeft, leftData] = self.CloneCamera(c,'_SLEFT')
			[cameraRight, rightData] = self.CloneCamera(c,'_SRIGHT')
			
			seg = self.CreateSegment(c, '_SEP', eyeSeparation)
			
			self.rigs += [[[cameraLeft, cameraRight], seg, c]]
			self.rig_cams_data += [leftData, rightData]
			print "Rig generated for ", c.getName(),"\n"
		print "All rigs generated\n"
		
	# Given a single stereo camera and its original camera, update the 
	# render a the current frame to disk
	def RenderFrame(self, frameNum, stereoCamera, origCamera):
		# Each camera outputs to its own directory to keep files better organized
		self.context.setRenderPath('%s/%s/%s/%s_' % (self.output_path_orig, origCamera.name, stereoCamera.name, stereoCamera.name))
		
		# Set new active camera
		self.scene.objects.camera = stereoCamera
	
		# Render and save a single frame to disk
		self.context.render()
		framestr = '%.4d' % frameNum
		self.context.saveRenderedImage(framestr)
		print '\n+++++++ Saved: ', self.context.getFrameFilename(), " +++++++ "
	
	
	# Render the animation by stepping by frame and rendering all 
	# cameras per frame.
	# 
	# TODO: Catch keyboard interrupt of rendering process
	def RenderAllRigsByFrame(self):
		self.GenerateStereoRigs(self.eyeSep)
		self.PrintStereoRigs()
		for frame in range(self.context.startFrame(), self.context.endFrame()+1): 
			print '\tRendering frame %i of %i.' % (frame, self.context.endFrame())
			self.context.currentFrame(frame)
		
			# loop over all the cameras in this scene, set active and render.
			for [[leftCam,rightCam], cameraSep, origCam] in self.rigs:
				# Get the new position, rotation, scale, etc from the original camera
				self.UpdateRig(leftCam,rightCam,cameraSep,origCam)
				self.RenderFrame(frame, leftCam, origCam)
				self.RenderFrame(frame, rightCam, origCam)
			print 'Animation Complete' 
	
	
	
	# Cleanup (NOTE: This is called by the garbage collector and guarantees we have
	# 			the opportunity to delete all stereo camera rigs)
	# 	1) Restore original settings
	#	2) Unlink the stereo rigs
	def __del__(self):
		# Restore original settings
		if self.orig_cam:
			self.scene.objects.camera = self.orig_cam
		self.context.setRenderPath(self.output_path_orig)

		print "Cleaning up stereo rigs"
		for [[l,r],s, o] in self.rigs:
			self.scene.objects.unlink(l)
			self.scene.objects.unlink(r)
			self.scene.objects.unlink(s)
			
		try: 
			del self.rigs
		except: 
			print "ERROR! Cannot del rig_cams!"		

		try: 
			del self.rig_cams_data
		except: 
			print "ERROR! Cannot del rig_cam_data!"		

		# NOTE: the camera data is not unlinked because its not possible to do that. 
		# 		When Blender quits the memory is deleted. If we call it by name we 
		#		can reuse the data
		print "Done with cleanup\n"
	
	
	
	
eyeSep = 6.3 * bu # cm 

# Properties needed: 
# Blender Units Scale (1 B.U. == ?? cm; typically 1 BU = 1 CM)
# Eye Separation: Standard is 6.3 cm
# 
# Render width ==> set in scene render panel (F10)
# Focal Dist ==> set in "DoF Dist" under Camera Edit panel (select Camera, F9) 
# FoV ==> set in "angle" property under camera (to set manually: 
#	select Camera, F9, "D" button and change Lens angle in Degrees instead of millimeters
# 
# Properties set: 
# 	CameraData.shiftX ==> horizontal offset in view (this is parallel stereo, not toed in)
# 	For details on "Asymmetric frustum parallel axis projection stereo"
# 	see http://www.orthostereo.com/geometryopengl.html
animator = StereoAnimator(Scene.GetCurrent(), eyeSep)
animator.RenderAllRigsByFrame()


# TODO: 
#	- Calculate the image cropping given eyeSeparation and dofDist in original cameraData
# 	- Perform crop on each frame
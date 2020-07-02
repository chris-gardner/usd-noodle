from pxr import Usd, Sdf, Ar

import os.path


def test(usdfile):
    print 'test'.center(40, '-')
    stage = Usd.Stage.Open(usdfile)
    
    print 'GetUsedLayers'.center(40, '-')
    # things that are in use, apparntly
    for x in stage.GetUsedLayers(includeClipLayers=True):
        print x
    #     print type(x)
    #     print dir(x)
    #     print x, x.GetFileFormat().GetFileExtensions()
    #     print 'subLayerPaths', x.subLayerPaths
    #
    # return
    
    print 'stage.Traverse'.center(40, '-')
    for prim in stage.Traverse():
        print(prim.GetPath())
        
        """Return a list of PrimSpecs that provide opinions for this prim (i.e.
        the prim's metadata fields, including composition metadata).
         specs are ordered from strongest to weakest opinion."""
        # print prim.GetPrimStack()
        
        if prim.HasAuthoredReferences():
            primSpec = stage.GetEditTarget().GetPrimSpecForScenePath(prim.GetPath())
            if primSpec:
                print 'primspec GetAssetInfo'
                print primSpec.assetInfo
                refList = primSpec.referenceList
                if refList:
                    print 'referenceList'.center(40, '-')
                    for ref in refList.GetAddedOrExplicitItems():
                        if ref.assetPath:
                            print ' -', ref.assetPath
                            print ' -', ref.customData
                            print ' -', ref.layerOffset
                
                refList = primSpec.payloadList
                if refList:
                    print 'payloadList'.center(40, '-')
                    for ref in refList.GetAddedOrExplicitItems():
                        if ref.assetPath:
                            print ' -', ref.assetPath
                
                refList = primSpec.specializesList
                if refList:
                    print 'specializesList'.center(40, '-')
                    for ref in refList.GetAddedOrExplicitItems():
                        if ref.assetPath:
                            print ' -', ref.assetPath
                
                refList = primSpec.inheritPathList
                if refList:
                    print 'inheritPathList'.center(40, '-')
                    for ref in refList.GetAddedOrExplicitItems():
                        if ref.assetPath:
                            print ' -', ref.assetPath
                
                print 'done with primspec'.center(40, '-')
        """
        this doesn't quite work
        https://groups.google.com/d/msg/usd-interest/s4AM0v60uBI/sYltgp7OAgAJ
        """
        if prim.HasPayload():
            print 'payloads'.center(40, '-')
            # this is apparently hacky, but it works, yah?
            # https://groups.google.com/d/msg/usd-interest/s4AM0v60uBI/q-okjU2RCAAJ
            payloads = prim.GetMetadata("payload")
            # so there's lots of lists
            for x in dir(payloads):
                if x.endswith('Items'):
                    print x, getattr(payloads, x)
            
            # query GetAddedOrExplicitItems for *all* entries, rather than rooting through each list?
            print 'GetAddedOrExplicitItems'
            print payloads.GetAddedOrExplicitItems()
            
            for itemlist in [payloads.appendedItems, payloads.explicitItems, payloads.addedItems,
                             payloads.prependedItems, payloads.orderedItems]:
                for payload in itemlist:
                    pathToResolve = payload.assetPath
                    print 'assetPath:', pathToResolve
                    primSpec = prim.GetPrimStack()[0]
                    # get the layer from the prim
                    anchorPath = primSpec.layer.identifier
                    
                    with Ar.ResolverContextBinder(stage.GetPathResolverContext()):
                        resolver = Ar.GetResolver()
                        # relative to layer path?
                        pathToResolve = resolver.AnchorRelativePath(anchorPath, pathToResolve)
                        print 'pathToResolve', pathToResolve
                        
                        # this should probably work, but no
                        resolvedPath = resolver.Resolve(pathToResolve)
                        print 'resolvedPath', resolvedPath
        
        if prim.HasAuthoredPayloads():
            payloads = prim.GetPayloads()
            # print payloads
            """
            There is currently no facility for listing the currently authored payloads on a prim...
            the problem is somewhat ill-defined, and requires some thought.
            """
        
        # does this prim have variant sets?
        if prim.HasVariantSets():
            print 'variantsets'.center(30, '-')
            
            # list all the variant sets avalable on this prim
            sets = prim.GetVariantSets()
            
            # you can't iterate over the sets.
            # you have to get the name and do a GetVariantSet(<<set name>>)
            # TypeError: 'VariantSets' object is not iterable
            # maybe USD 20?
            for varset in sets.GetNames():
                print 'variant set name:', varset
                # get the variant set by name
                thisvarset = prim.GetVariantSet(varset)
                
                # the available variants
                print thisvarset.GetVariantNames()
                # the current variant
                print thisvarset.GetVariantSelection()
                print varset
        
        # gotta get a clip on each prim and then test it for paths?
        clips = Usd.ClipsAPI(prim)
        if clips.GetClipAssetPaths():
            print 'CLIPS'.center(30, '-')
            # dict of clip info. full of everything
            # key is the clip *name*
            print clips.GetClips()
            # this is a good one - resolved asset paths too
            for path in clips.GetClipAssetPaths():
                print path, type(path)
                print path.resolvedPath
            print 'GetClipPrimPath', clips.GetClipPrimPath()
        
        mdlinfo = Usd.ModelAPI(prim)
        print 'UsdModelAPI'.center(30, '-')
        print mdlinfo
        print 'GetAssetInfo', mdlinfo.GetAssetInfo()
        print 'GetAssetIdentifier', mdlinfo.GetAssetIdentifier()
        print 'GetKind', mdlinfo.GetKind()
        print 'GetPayloadAssetDependencies', mdlinfo.GetPayloadAssetDependencies()
        
        primStack = prim.GetPrimStack()
        print 'GetPrimStack'.center(30, '-')
        for spec in primStack:
            print spec
            
            print 'layer.realPath', spec.layer.realPath
            print 'path.pathString', spec.path.pathString
            print 'layer.identifier', spec.layer.identifier
            print 'GetPayloadList', spec.payloadList
            print '--'
        
        print prim.HasPayload()
        print prim.HasAuthoredPayloads()
    
    print 'end test'.center(40, '-')


def prim_traverse(usdfile):
    ret = []
    stage = Usd.Stage.Open(usdfile)
    
    for prim in stage.Traverse():
        
        """
        this doesn't quite work
        https://groups.google.com/d/msg/usd-interest/s4AM0v60uBI/sYltgp7OAgAJ
        """
        if prim.HasPayload():
            print 'payloads'.center(40, '-')
            # this is apparently hacky, but it works, yah?
            # https://groups.google.com/d/msg/usd-interest/s4AM0v60uBI/q-okjU2RCAAJ
            payloads = prim.GetMetadata("payload")
            # so there's lots of lists
            for x in dir(payloads):
                if x.endswith('Items'):
                    print x, getattr(payloads, x)
            
            for itemlist in [payloads.appendedItems, payloads.explicitItems, payloads.addedItems,
                             payloads.prependedItems, payloads.orderedItems]:
                for payload in itemlist:
                    pathToResolve = payload.assetPath
                    print 'assetPath:', pathToResolve
                    primSpec = prim.GetPrimStack()[0]
                    # get the layer from the prim
                    anchorPath = primSpec.layer.identifier
                    print 'anchorPath', anchorPath
                    with Ar.ResolverContextBinder(stage.GetPathResolverContext()):
                        resolver = Ar.GetResolver()
                        # relative to layer path? NOPE
                        # problem here is that the layer path is NOT
                        # really what the payload path is relative to
                        # and why it's better to go through the primstack - you can get a
                        # proper anchor path
                        pathToResolve = resolver.AnchorRelativePath(anchorPath, pathToResolve)
                        print 'pathToResolve', pathToResolve
                        
                        # this should probably work, but no
                        resolvedPath = resolver.Resolve(pathToResolve)
                        print 'resolvedPath', resolvedPath
        
        # does this prim have variant sets?
        if prim.HasVariantSets():
            print 'variantsets'.center(30, '-')
            
            # list all the variant sets avalable on this prim
            sets = prim.GetVariantSets()
            
            # you can't iterate over the sets.
            # you have to get the name and do a GetVariantSet(<<set name>>)
            # TypeError: 'VariantSets' object is not iterable
            # maybe USD 20?
            for varset in sets.GetNames():
                print 'variant set name:', varset
                # get the variant set by name
                thisvarset = prim.GetVariantSet(varset)
                
                # the available variants
                print 'variant names:', thisvarset.GetVariantNames()
                # the current variant
                print 'current variant:', thisvarset.GetVariantSelection()
                print varset
                print thisvarset.GetPrim()
        
        # gotta get a clip on each prim and then test it for paths?
        clips = Usd.ClipsAPI(prim)
        if clips.GetClipAssetPaths():
            print 'CLIPS'.center(30, '-')
            # dict of clip info. full of everything
            # key is the clip *name*
            print clips.GetClips()
            # this is a good one - resolved asset paths too
            for path in clips.GetClipAssetPaths():
                print path, type(path)
                print path.resolvedPath
            print 'GetClipPrimPath', clips.GetClipPrimPath()
        
        # from the docs:
        """Return a list of PrimSpecs that provide opinions for this prim (i.e.
        the prim's metadata fields, including composition metadata).
         specs are ordered from strongest to weakest opinion."""
        primStack = prim.GetPrimStack()
        print 'GetPrimStack'.center(30, '-')
        for spec in primStack:
            # print spec
            ret.append(spec.path.pathString)
            # print 'layer.realPath', spec.layer.realPath
            print 'path.pathString', spec.path.pathString
            print 'layer.identifier', spec.layer.identifier
            print 'layer.owner', spec.layer.owner
            print 'layer.subLayerPaths', spec.layer.subLayerPaths
            if spec.hasPayloads:
                print 'GetPayloadList', spec.payloadList
                for itemlist in [spec.payloadList.appendedItems, spec.payloadList.explicitItems,
                                 spec.payloadList.addedItems,
                                 spec.payloadList.prependedItems, spec.payloadList.orderedItems]:
                    if itemlist:
                        for payload in itemlist:
                            payload_path = payload.assetPath
                            
                            print payload, payload_path
                            with Ar.ResolverContextBinder(stage.GetPathResolverContext()):
                                resolver = Ar.GetResolver()
                                # we resolve the payload path realtive to the primSpec layer path (layer.identifier)
                                # far more likely to be correct. i hope
                                resolvedpath = resolver.AnchorRelativePath(spec.layer.identifier, payload_path)
                                print 'payload resolvedpath', resolvedpath
                
            
            # if spec.hasSpecializes:
            # print 'specializesList', spec.specializesList
            if spec.hasReferences:
                print 'referenceList', spec.referenceList
            # if spec.hasVariantSetNames:
            # print dir(spec)
            if spec.variantSets:
                print 'variantSets', spec.variantSets
                for varset in spec.variantSets:
                    # SdfVariantSetSpec objects
                    print varset
                    print 'variant set name', varset.name
                    print 'owner', varset.owner
                    print 'isInert', varset.isInert
                    print 'layer', varset.layer
                    
                    # the available variants
                    # dict with the variant name as a key nad a Sdf.Find object as the value
                    print 'variant', varset.variants
                    print 'variant_names:', varset.variants.keys()
                    # the current variant?
                    print 'variantList', varset.variantList
                    
                    # SdfVariantSetSpec doesn't seem to know which is the current variant
                    # but it's a short hop to get the variant set object
                    # and perhaps this is the best of both worlds
                    thisvarset = prim.GetVariantSet(varset.name)
                    print 'current variant:', thisvarset.GetVariantSelection()
                    
                    # print 'GetVariantNames', spec.GetVariantNames(varset)
            # def, over or class
            print 'GetSpecifier', spec.specifier
            # component,
            print 'GetKind', spec.kind
            print '--'
        
        print prim.HasPayload()
        print prim.HasAuthoredPayloads()
    return ret


def walkStageLayers(layer, level=1):
    # cut down verion of our recursive layer walk function
    layer_path = layer.realPath
    ret = [layer_path]
    layer_basepath = os.path.dirname(layer_path)
    count = 0
    
    for ref in layer.GetExternalReferences():
        if not ref:
            # sometimes a ref can be a zero length string. whyyyyyyyyy?
            # seeing this in multiverse esper_room example
            continue
        
        refpath = os.path.normpath(os.path.join(layer_basepath, ref))
        
        # if you wanna construct a full path yourself
        # you can manually load a SdfLayer like this
        # sub_layer = Sdf.Layer.Find(refpath)
        
        # or you can use FindRelativeToLayer to do the dirty work
        # seems to operate according to the composition rules (variants blah blah)
        # ie, it *may* not return a layer if the stage is set to not load that layer
        sub_layer = Sdf.Layer.FindRelativeToLayer(layer, ref)
        
        if sub_layer:
            ret.extend(walkStageLayers(sub_layer, level=level + 1))
    return ret


def layer_walk_exploring(usdfile):
    print 'layer_walk_exploring'.center(40, '-')
    stage = Usd.Stage.Open(usdfile)
    rootLayer = stage.GetRootLayer()
    
    used_layers = []
    print 'GetUsedLayers'.center(40, '-')
    # things that are in use, apparntly
    # includeClipLayers, like the googles, appear to do nothing
    for x in stage.GetUsedLayers(includeClipLayers=False):
        used_layers.append(x.realPath)
    used_layers = set(used_layers)
    print 'used_layers'.center(20, '-')
    print used_layers
    
    walk_layers = set(walkStageLayers(rootLayer))
    print 'walk_layers'.center(20, '-')
    print walk_layers
    
    print 'diff:'.center(20, '-')
    print walk_layers.difference(used_layers)
    
    # so layer walk and getUsedLayers appear to give the same results
    # getUsedLayers may be faster, given that it's not recursive
    # programming blah blah blah
    # disadvantage is that it doesn't give you the *relationships* between the layers
    # which is what we're interested in here
    
    prim_stack = prim_traverse(usdfile)
    prim_stack = set(prim_stack)
    # print 'prim_stack:'.center(20, '-')
    # print prim_stack
    print 'diff:'.center(20, '-')
    print walk_layers.difference(prim_stack)
    
    print 'layer_walk_exploring'.center(40, '-')

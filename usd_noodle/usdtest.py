from __future__ import print_function

from pxr import Usd, Sdf, Ar, UsdUtils

import os.path
from pprint import pprint


def test(usdfile):
    print('test'.center(40, '-'))
    stage = Usd.Stage.Open(usdfile)
    
    print('GetUsedLayers'.center(40, '-'))
    # things that are in use, apparntly
    for x in stage.GetUsedLayers(includeClipLayers=True):
        print(x)
    #     print(type(x))
    #     print(dir(x))
    #     print(x, x.GetFileFormat().GetFileExtensions())
    #     print('subLayerPaths', x.subLayerPaths)
    #
    # return
    
    print('stage.Traverse'.center(40, '-'))
    for prim in stage.Traverse():
        print(prim.GetPath())
        
        """Return a list of PrimSpecs that provide opinions for this prim (i.e.
        the prim's metadata fields, including composition metadata).
         specs are ordered from strongest to weakest opinion."""
        # print(prim.GetPrimStack())
        
        if prim.HasAuthoredReferences():
            primSpec = stage.GetEditTarget().GetPrimSpecForScenePath(prim.GetPath())
            if primSpec:
                print('primspec GetAssetInfo')
                print(primSpec.assetInfo)
                refList = primSpec.referenceList
                if refList:
                    print('referenceList'.center(40, '-'))
                    for ref in refList.GetAddedOrExplicitItems():
                        if ref.assetPath:
                            print(' -', ref.assetPath)
                            print(' -', ref.customData)
                            print(' -', ref.layerOffset)
                
                refList = primSpec.payloadList
                if refList:
                    print('payloadList'.center(40, '-'))
                    for ref in refList.GetAddedOrExplicitItems():
                        if ref.assetPath:
                            print(' -', ref.assetPath)
                
                refList = primSpec.specializesList
                if refList:
                    print('specializesList'.center(40, '-'))
                    for ref in refList.GetAddedOrExplicitItems():
                        if ref.assetPath:
                            print(' -', ref.assetPath)
                
                refList = primSpec.inheritPathList
                if refList:
                    print('inheritPathList'.center(40, '-'))
                    for ref in refList.GetAddedOrExplicitItems():
                        if ref.assetPath:
                            print(' -', ref.assetPath)
                
                print('done with primspec'.center(40, '-'))
        """
        this doesn't quite work
        https://groups.google.com/d/msg/usd-interest/s4AM0v60uBI/sYltgp7OAgAJ
        """
        if prim.HasPayload():
            print('payloads'.center(40, '-'))
            # this is apparently hacky, but it works, yah?
            # https://groups.google.com/d/msg/usd-interest/s4AM0v60uBI/q-okjU2RCAAJ
            payloads = prim.GetMetadata("payload")
            # so there's lots of lists
            for x in dir(payloads):
                if x.endswith('Items'):
                    print(x, getattr(payloads, x))
            
            # query GetAddedOrExplicitItems for *all* entries, rather than rooting through each list?
            print('GetAddedOrExplicitItems')
            print(payloads.GetAddedOrExplicitItems())
            
            for itemlist in [payloads.appendedItems, payloads.explicitItems, payloads.addedItems,
                             payloads.prependedItems, payloads.orderedItems]:
                for payload in itemlist:
                    pathToResolve = payload.assetPath
                    print('assetPath:', pathToResolve)
                    primSpec = prim.GetPrimStack()[0]
                    # get the layer from the prim
                    anchorPath = primSpec.layer.identifier
                    
                    with Ar.ResolverContextBinder(stage.GetPathResolverContext()):
                        resolver = Ar.GetResolver()
                        # relative to layer path?
                        pathToResolve = resolver.AnchorRelativePath(anchorPath, pathToResolve)
                        print('pathToResolve', pathToResolve)
                        
                        # this should probably work, but no
                        resolvedPath = resolver.Resolve(pathToResolve)
                        print('resolvedPath', resolvedPath)
        
        if prim.HasAuthoredPayloads():
            payloads = prim.GetPayloads()
            # print(payloads)
            """
            There is currently no facility for listing the currently authored payloads on a prim...
            the problem is somewhat ill-defined, and requires some thought.
            """
        
        # does this prim have variant sets?
        if prim.HasVariantSets():
            print('variantsets'.center(30, '-'))
            
            # list all the variant sets avalable on this prim
            sets = prim.GetVariantSets()
            
            # you can't iterate over the sets.
            # you have to get the name and do a GetVariantSet(<<set name>>)
            # TypeError: 'VariantSets' object is not iterable
            # maybe USD 20?
            for varset in sets.GetNames():
                print('variant set name:', varset)
                # get the variant set by name
                thisvarset = prim.GetVariantSet(varset)
                
                # the available variants
                print(thisvarset.GetVariantNames())
                # the current variant
                print(thisvarset.GetVariantSelection())
                print(varset)
        
        # gotta get a clip on each prim and then test it for paths?
        clips = Usd.ClipsAPI(prim)
        if clips.GetClipAssetPaths():
            print('CLIPS'.center(30, '-'))
            # dict of clip info. full of everything
            # key is the clip *name*
            print(clips.GetClips())
            # this is a good one - resolved asset paths too
            for path in clips.GetClipAssetPaths():
                print(path, type(path))
                print(path.resolvedPath)
            print('GetClipPrimPath', clips.GetClipPrimPath())
        
        mdlinfo = Usd.ModelAPI(prim)
        print('UsdModelAPI'.center(30, '-'))
        print(mdlinfo)
        print('GetAssetInfo', mdlinfo.GetAssetInfo())
        print('GetAssetIdentifier', mdlinfo.GetAssetIdentifier())
        print('GetKind', mdlinfo.GetKind())
        print('GetPayloadAssetDependencies', mdlinfo.GetPayloadAssetDependencies())
        
        primStack = prim.GetPrimStack()
        print('GetPrimStack'.center(30, '-'))
        for spec in primStack:
            print(spec)
            
            print('layer.realPath', spec.layer.realPath)
            print('path.pathString', spec.path.pathString)
            print('layer.identifier', spec.layer.identifier)
            print('GetPayloadList', spec.payloadList)
            print('--')
        
        print(prim.HasPayload())
        print(prim.HasAuthoredPayloads())
    
    print('end test'.center(40, '-'))


def prim_traverse(usdfile):
    ret = []
    stage = Usd.Stage.Open(usdfile)
    count = 1
    
    for prim in stage.Traverse():
        
        """
        this doesn't quite work
        https://groups.google.com/d/msg/usd-interest/s4AM0v60uBI/sYltgp7OAgAJ
        """
        if prim.HasPayload():
            print('payloads'.center(40, '-'))
            # this is apparently hacky, but it works, yah?
            # https://groups.google.com/d/msg/usd-interest/s4AM0v60uBI/q-okjU2RCAAJ
            payloads = prim.GetMetadata("payload")
            # so there's lots of lists
            for x in dir(payloads):
                if x.endswith('Items'):
                    print(x, getattr(payloads, x))
            
            for itemlist in [payloads.appendedItems, payloads.explicitItems, payloads.addedItems,
                             payloads.prependedItems, payloads.orderedItems]:
                for payload in itemlist:
                    pathToResolve = payload.assetPath
                    print('assetPath:', pathToResolve)
                    primSpec = prim.GetPrimStack()[0]
                    # get the layer from the prim
                    anchorPath = primSpec.layer.identifier
                    print('anchorPath', anchorPath)
                    with Ar.ResolverContextBinder(stage.GetPathResolverContext()):
                        resolver = Ar.GetResolver()
                        # relative to layer path? NOPE
                        # problem here is that the layer path is NOT
                        # really what the payload path is relative to
                        # and why it's better to go through the primstack - you can get a
                        # proper anchor path
                        pathToResolve = resolver.AnchorRelativePath(anchorPath, pathToResolve)
                        print('pathToResolve', pathToResolve)
                        
                        # this should probably work, but no
                        resolvedPath = resolver.Resolve(pathToResolve)
                        print('resolvedPath', resolvedPath)
        
        # does this prim have variant sets?
        if prim.HasVariantSets():
            print('variantsets'.center(30, '-'))
            
            # list all the variant sets avalable on this prim
            sets = prim.GetVariantSets()
            
            # you can't iterate over the sets.
            # you have to get the name and do a GetVariantSet(<<set name>>)
            # TypeError: 'VariantSets' object is not iterable
            # maybe USD 20?
            for varset in sets.GetNames():
                print('variant set name:', varset)
                # get the variant set by name
                thisvarset = prim.GetVariantSet(varset)
                
                # the available variants
                print('variant names:', thisvarset.GetVariantNames())
                # the current variant
                print('current variant:', thisvarset.GetVariantSelection())
                print(varset)
                print(thisvarset.GetPrim())
        
        # clips - this seems to be the way to do things
        # clips are not going to be picked up by the stage layers inspection stuff
        # apparently they're expensive. whatever.
        # no prim stack shennanigans for us
        # gotta get a clip on each prim and then test it for paths?
        clips = Usd.ClipsAPI(prim)
        if clips.GetClipAssetPaths():
            print('CLIPS'.center(30, '-'))
            # dict of clip info. full of everything
            # key is the clip set *name*
            print(clips.GetClips())
            
            # GetClipSets seems to be crashing this houdini build - clips.GetClipSets()
            clip_sets = clips.GetClips().keys()
            print('clip_sets', clip_sets)
            
            # this is a good one - resolved asset paths too
            for clipSet in clip_sets:
                print('CLIP_SET:', clipSet)
                for path in clips.GetClipAssetPaths(clipSet):
                    print(path, type(path))
                    print('resolved path:', path.resolvedPath)
                    ret.append(path.resolvedPath)
                
                print('GetClipTemplateAssetPath:', clips.GetClipTemplateAssetPath(clipSet))
                print('GetClipAssetPaths:', clips.GetClipAssetPaths())
            
            print('GetClipPrimPath', clips.GetClipPrimPath())
        
        # from the docs:
        """Return a list of PrimSpecs that provide opinions for this prim (i.e.
        the prim's metadata fields, including composition metadata).
         specs are ordered from strongest to weakest opinion."""
        primStack = prim.GetPrimStack()
        print('GetPrimStack'.center(30, '-'))
        for spec in primStack:
            # print(spec)
            # print('layer.realPath', spec.layer.realPath)
            print('path.pathString', spec.path.pathString)
            print('layer.identifier', spec.layer.identifier)
            print('layer.owner', spec.layer.owner)
            print('layer.subLayerPaths', spec.layer.subLayerPaths)
            print('specifier', spec.specifier)
            # if not spec.variantSets:
            
            if spec.hasPayloads:
                print('GetPayloadList'.center(80, '#'))
                payloadList = spec.payloadList
                print('GetPayloadList', payloadList)
                for itemlist in [payloadList.appendedItems, payloadList.explicitItems,
                                 payloadList.addedItems,
                                 payloadList.prependedItems, payloadList.orderedItems]:
                    if itemlist:
                        for payload in itemlist:
                            payload_path = payload.assetPath
                            
                            print(payload, payload_path)
                            with Ar.ResolverContextBinder(stage.GetPathResolverContext()):
                                resolver = Ar.GetResolver()
                                # we resolve the payload path relative to the primSpec layer path (layer.identifier)
                                # far more likely to be correct. i hope
                                resolvedpath = resolver.AnchorRelativePath(spec.layer.identifier, payload_path)
                                print('payload resolvedpath', resolvedpath)
                                ret.append(resolvedpath)
            
            # the docs say there's a HasSpecializes method
            # no, there is not. at least in this build of houdini 18.0.453
            # if spec.HasSpecializes:
            # let's just ignore specialize for the time being
            """
            specializesList = spec.specializesList
            spec_paths = []
            for itemlist in [specializesList.appendedItems, specializesList.explicitItems,
                             specializesList.addedItems,
                             specializesList.prependedItems, specializesList.orderedItems]:
                if itemlist:
                    for specialize in itemlist:
                        specialize_path = specialize.assetPath
                        with Ar.ResolverContextBinder(stage.GetPathResolverContext()):
                            resolver = Ar.GetResolver()
                            resolvedpath = resolver.AnchorRelativePath(spec.layer.identifier, specialize_path)
                            spec_paths.append(resolvedpath)
                            ret.append(resolvedpath)
                            
            if spec_paths:
                print('specializesList', spec.specializesList)

            """
            
            # references operate the same to payloads
            if spec.hasReferences:
                reflist = spec.referenceList
                print('referenceList', reflist)
                print('orderedItems', reflist.orderedItems)
                for itemlist in [reflist.appendedItems, reflist.explicitItems,
                                 reflist.addedItems,
                                 reflist.prependedItems, reflist.orderedItems]:
                    if itemlist:
                        for reference in itemlist:
                            print('reference:', reference)
                            reference_path = reference.assetPath
                            with Ar.ResolverContextBinder(stage.GetPathResolverContext()):
                                resolver = Ar.GetResolver()
                                # we resolve the payload path relative to the primSpec layer path (layer.identifier)
                                # far more likely to be correct. i hope
                                resolvedpath = resolver.AnchorRelativePath(spec.layer.identifier, reference_path)
                                print('reference resolvedpath', resolvedpath)
                                ret.append(resolvedpath)
            
            # if spec.hasVariantSetNames:
            # print(dir(spec))
            if spec.variantSets:
                print('variantSets', spec.variantSets)
                for varset in spec.variantSets:
                    # SdfVariantSetSpec objects
                    print(varset)
                    
                    # you can get a SdfPath from the variant path
                    # https://groups.google.com/d/msg/usd-interest/Q1tjV88T1EI/_KGo3wzyBAAJ
                    variantDefinitionPath = Sdf.Path(varset.path)
                    print('---variantDefinitionPath')
                    print('variantDefinitionPath', variantDefinitionPath)
                    print(type(variantDefinitionPath))
                    print(dir(variantDefinitionPath))
                    print('pathString', variantDefinitionPath.pathString)
                    print('GetParentPath', variantDefinitionPath.GetParentPath())
                    print('GetPrimOrPrimVariantSelectionPath',
                          variantDefinitionPath.GetPrimOrPrimVariantSelectionPath())
                    print('GetPrimPath', variantDefinitionPath.GetPrimPath())
                    print('GetVariantSelection', variantDefinitionPath.GetVariantSelection())
                    print('isAbsolutePath', variantDefinitionPath.IsAbsolutePath())
                    print('IsPrimVariantSelectionPath', variantDefinitionPath.IsPrimVariantSelectionPath())
                    print('GetTargetPath', variantDefinitionPath.targetPath)
                    
                    pld = Sdf.Payload(variantDefinitionPath.pathString)
                    print(pld)
                    print(pld.assetPath)
                    print(dir(pld))
                    
                    print('---variantDefinitionPath')
                    
                    print('variant set name', varset.name)
                    print('owner', varset.owner)
                    print('isInert', varset.isInert)
                    print('layer', varset.layer)
                    
                    # the available variants
                    # dict with the variant name as a key nad a Sdf.Find object as the value
                    print('variant', varset.variants)
                    print('variant_names:', varset.variants.keys())
                    
                    # SdfVariantSetSpec doesn't seem to know which is the current variant
                    # but it's a short hop to get the variant set object
                    # and perhaps this is the best of both worlds
                    thisvarset = prim.GetVariantSet(varset.name)
                    current_variant_name = thisvarset.GetVariantSelection()
                    print('current variant name:', current_variant_name)
                    current_variant = varset.variants[current_variant_name]
                    
                    for variant_name in varset.variants.keys():
                        variant = varset.variants[variant_name]
                        print(variant.GetPrimStack())
                        
                        print('variant:', variant)
                        print('path:', variant.path)
                        print('layer:', variant.layer)
                        print('variant payload info:', variant.GetInfo('payload'))
                        payloads = variant.GetInfo('payload')
                        for itemlist in [payloads.appendedItems, payloads.explicitItems, payloads.addedItems,
                                         payloads.prependedItems, payloads.orderedItems]:
                            for payload in itemlist:
                                pathToResolve = payload.assetPath
                                anchorPath = variant.layer.identifier
                                print('anchorPath', anchorPath)
                                with Ar.ResolverContextBinder(stage.GetPathResolverContext()):
                                    resolver = Ar.GetResolver()
                                    pathToResolve = resolver.AnchorRelativePath(anchorPath, pathToResolve)
                                    print('pathToResolve', pathToResolve)
                    
                    # print(type(current_variant))
                    # print(dir(current_variant))
                    # print('path', current_variant.path)
                    # print('variantSets', current_variant.variantSets)
                    # print('layer', current_variant.layer)
                    # print('GetMetaDataInfoKeys', current_variant.GetMetaDataInfoKeys())
                    # print('variant payload info:', current_variant.GetInfo('payload'))
                    #
                    for key in current_variant.GetMetaDataInfoKeys():
                        print(key, current_variant.GetInfo(key))
                    
                    # THIS IS WAAAY WRONG
                    # it's just giving the layer path
                    current_variant_path = current_variant.layer.realPath
                    # the paths we are looking for are coming in as payloads
                    # (because they can be dynamically loaded i guess)
                    
                    print(current_variant_path)
                    
                    x = thisvarset.GetVariantEditTarget()
                    
                    count += 1
                if count > 1:
                    print('count', count)
                    raise RuntimeError("poo")
                
                # print('GetVariantNames', spec.GetVariantNames(varset))
            # def, over or class
            print('GetSpecifier', spec.specifier)
            # component,
            
            print('GetInherits')
            inherits = prim.GetInherits().GetAllDirectInherits()
            if inherits:
                print(inherits)
                raise RuntimeError('poo')
            
            print('GetKind', spec.kind)
            print('--')
        
        print(prim.HasPayload())
        print(prim.HasAuthoredPayloads())
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
    print('layer_walk_exploring'.center(40, '-'))
    stage = Usd.Stage.Open(usdfile)
    rootLayer = stage.GetRootLayer()
    
    used_layers = []
    print('GetUsedLayers'.center(40, '-'))
    # things that are in use, apparntly
    # includeClipLayers, like the googles, appear to do nothing
    for x in stage.GetUsedLayers(includeClipLayers=False):
        used_layers.append(x.realPath)
    used_layers = set(used_layers)
    print('used_layers'.center(20, '-'))
    print(used_layers)
    
    walk_layers = set(walkStageLayers(rootLayer))
    print('walk_layers'.center(20, '-'))
    print(walk_layers)
    
    print('diff:'.center(20, '-'))
    print(walk_layers.difference(used_layers))
    
    # so layer walk and getUsedLayers appear to give the same results
    # getUsedLayers may be faster, given that it's not recursive
    # programming blah blah blah
    # disadvantage is that it doesn't give you the *relationships* between the layers
    # which is what we're interested in here
    
    prim_stack = prim_traverse(usdfile)
    prim_stack = set(prim_stack)
    
    # print('prim_stack:'.center(20, '-'))
    # print(prim_stack)
    # print('walk_layers:'.center(20, '-'))
    # print(walk_layers)
    
    print('diff:'.center(20, '-'))
    print(prim_stack.difference(walk_layers))
    
    print('layer_walk_exploring'.center(40, '-'))


def pcp(usdfile):
    print('pcp'.center(40, '-'))
    stage = Usd.Stage.Open(usdfile)
    count = 1
    
    for prim in stage.Traverse():
        prim_idx = prim.GetPrimIndex()
        # print(dir(prim_idx))
        # print(prim_idx.DumpToString())
        print(prim_idx.hasAnyPayloads)
        root_node = prim_idx.rootNode
        # print(dir(root_node))
        print('arcType', root_node.arcType)
        print('path', root_node.path)
        print('layerStack', root_node.layerStack)
        print('site', root_node.site)
        # print('site', root_node.site.path.string)
        print(type(root_node.site))
        print(dir(root_node.site.path))
        if 'Dressoire' in str(root_node.site.path):
            raise RuntimeError("poo")
        
        if prim_idx.ComposeAuthoredVariantSelections():
            print(prim_idx.ComposeAuthoredVariantSelections())
        if prim_idx.ComputePrimPropertyNames():
            print(prim_idx.ComputePrimPropertyNames())
    print('pcp'.center(40, '-'))


def dep(usdfile, level=1):
    id = '-' * (level)
    
    # print('UsdUtilsExtractExternalReferences'.center(40, '-'))
    print(id, usdfile)
    sublayers, references, payloads = UsdUtils.ExtractExternalReferences(usdfile)
    
    if sublayers:
        print(id, 'SUBLAYERS')
        for sublayer in sublayers:
            # print(id, sublayer)
            refpath = os.path.normpath(os.path.join(os.path.dirname(usdfile), sublayer))
            dep(refpath, level=level + 1)
    
    if references:
        print(id, 'REFERENCES')
        for reference in references:
            # print(id, reference)
            refpath = os.path.normpath(os.path.join(os.path.dirname(usdfile), reference))
            dep(refpath, level=level + 1)
    
    if payloads:
        print(id, 'PAYLOADS')
        for payload in payloads:
            # print(id, payload)
            refpath = os.path.normpath(os.path.join(os.path.dirname(usdfile), payload))
            dep(refpath, level=level + 1)


def get_flat_child_list(path):
    ret = [path]
    for key, child in path.nameChildren.items():
        ret.extend(get_flat_child_list(child))
    ret = list(set(ret))
    return ret


def dep_2(usdfile, level=1):
    id = '-' * (level)
    
    sublayers = []
    payloads = []
    references = []
    
    layer = Sdf.Layer.FindOrOpen(usdfile)
    if not layer:
        return
    print(id, layer.realPath, type(layer))
    root = layer.pseudoRoot
    print(id, 'root', root)
    # print(dir(layer))
    # print(id, 'children'.center(40, '-'))
    
    child_list = get_flat_child_list(root)
    
    for child in child_list:
        print(id, child, type(child))
        
        attributes = child.attributes
        if attributes:
            print('attributes'.center(40, '-'))
            
            for attr in attributes:
                if attr.typeName == 'asset':
                    value = attr.default
                    if value:
                        print(dir(child))
                        # parent of this object
                        print('realNameParent', child.realNameParent)
                        # path to the thing hosting the attribute
                        print('path', child.path)
                        print('name', child.name)
                        # type of def - eg "shader"
                        print('typeName', child.typeName)
                        
                        print('ASSET')
                        print(attr, type(attr))
                        print(dir(attr))
                        print('attr displayName:', attr.displayName)
                        print('attr path:', attr.path)
                        print('attr name:', attr.name)
                        print('attr typeName:', attr.typeName)
                        print('attr valueType:', attr.valueType)
                        print('attr owner:', attr.owner)
                        print('attr roleName:', attr.roleName)
                        print('attr colorSpace:', attr.colorSpace)
                        
                        print(value, type(value))
                        print(dir(value))
                        print(value.path)
                        if value.path:
                            resolved_path = Sdf.ComputeAssetPathRelativeToLayer(layer, value.path)
                            print(resolved_path, os.path.isfile(resolved_path))
                    # print(dir(attr))
                    # print(attr.GetConciseRelativePaths())
                    # connpaths = attr.connectionPathList
                    # print(connpaths)
                    # # print(type(connpaths))
                    # for itemlist in [connpaths.appendedItems, connpaths.explicitItems, connpaths.addedItems,
                    #                  connpaths.prependedItems, connpaths.orderedItems]:
                    #     for item in itemlist:
                    #         print(item, type(item))
                    # # print(attr.ConnectionPathsKey)
                    # print('assetInfo', attr.assetInfo)
                    # print('allowedTokens', attr.allowedTokens)
                    # print('displayUnit', attr.displayUnit)
                    # print('roleName', attr.roleName)
                    # print('valueType', attr.valueType)
                    # print('name', attr.name)
                    # print('default', attr.default)
                    
                    # print(attr.path)
                    # print(layer.ListTimeSamplesForPath(attr.path))
                    # print(layer.QueryTimeSample(attr.path, 0))
                    # print('assetInfo', attr.typeName, type(attr.typeName))
                    # if attr.HasConnectionPaths():
                    #     print(attr.GetConnectionPathList())
            
            print('END attributes'.center(40, '-'))
        # print('properties'.center(40, '-'))
        # for prop in child.properties:
        #     print(prop, type(prop))
        #     # print(dir(prop))
        #     # print('assetInfo', prop.assetInfo)
        #     # print('rolename:', prop.roleName)
        #     # print('GetAllowedTokens:', prop.allowedTokens)
        #     connpaths = prop.typeName
        #     connpaths = prop.connectionPathList
        #     print(connpaths)
        #     # print(type(connpaths))
        #     for itemlist in [connpaths.appendedItems, connpaths.explicitItems, connpaths.addedItems,
        #                      connpaths.prependedItems, connpaths.orderedItems]:
        #         for item in itemlist:
        #             print(item, type(item))
        #
        # print('END properties'.center(40, '-'))
        
        # for key in child.ListInfoKeys():
        #     print(child.GetInfo(key))
        #
        # print(child.GetMetaDataInfoKeys())
        
        # raise RuntimeError("poo")
        
        clip_info = child.GetInfo("clips")
        # pprint(clip_info)
        
        # for clip_set_name in clip_info:
        #     clip_set = clip_info[clip_set_name]
        #     print(clip_set.keys())
        #     pprint(clip_set)
        #     print(clip_set_name, clip_set.get("assetPaths"), clip_set.get("manifestAssetPath"), clip_set.get("primPath"))
        #     for assetPath in clip_set.get("assetPaths"):
        #         print(id, Sdf.ComputeAssetPathRelativeToLayer(layer, assetPath.path))
        #     manifestPath = clip_set.get("manifestAssetPath")
        #     print(manifestPath, type(manifestPath))
        #     print(id, Sdf.ComputeAssetPathRelativeToLayer(layer, manifestPath.path))
        
        if child.variantSets:
            print('variants'.center(40, '-'))
            for varset in child.variantSets:
                print(varset.name)
                for variant_name in varset.variants.keys():
                    variant = varset.variants[variant_name]
                    print(variant_name)
                    payloadList = variant.primSpec.payloadList
                    print(payloadList)
                    for x in get_flat_child_list(variant.primSpec):
                        print(x.payloadList)
                        print(x.referenceList)
        
        payloadList = child.payloadList
        for itemlist in [payloadList.appendedItems, payloadList.explicitItems, payloadList.addedItems,
                         payloadList.prependedItems, payloadList.orderedItems]:
            for payload in itemlist:
                pathToResolve = payload.assetPath
                if pathToResolve:
                    refpath = os.path.normpath(os.path.join(os.path.dirname(layer.realPath), pathToResolve)).replace(
                        '\\', '/')
                    # print(id, 'payload:', refpath)
                    payloads.append(refpath)
        
        referenceList = child.referenceList
        for itemlist in [referenceList.appendedItems, referenceList.explicitItems, referenceList.addedItems,
                         referenceList.prependedItems, referenceList.orderedItems]:
            for reference in itemlist:
                pathToResolve = reference.assetPath
                if pathToResolve:
                    refpath = os.path.normpath(os.path.join(os.path.dirname(layer.realPath), pathToResolve)).replace(
                        '\\', '/')
                    # print(id, 'payload:', refpath)
                    references.append(refpath)
    
    for rel_sublayer in layer.subLayerPaths:
        refpath = os.path.normpath(os.path.join(os.path.dirname(layer.realPath), rel_sublayer)).replace('\\', '/')
        sublayers.append(refpath)
        # print(id, refpath)
        dep_2(refpath, level=level + 1)
        # sub_layer = Sdf.Layer.FindOrOpen(refpath)
        # print(sub_layer)
        #
    sublayers = list(set(sublayers))
    references = list(set(references))
    payloads = list(set(payloads))
    
    print(id, 'sublayerPaths'.center(40, '-'))
    print(id, sublayers)
    print(id, 'references'.center(40, '-'))
    print(id, references)
    print(id, 'payloads'.center(40, '-'))
    print(id, payloads)

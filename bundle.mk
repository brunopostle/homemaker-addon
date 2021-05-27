VERSION:=`date '+%Y-%m-%d'`
PYVERSION:=py39
PLATFORM:=linux-x86_64

dist:
	rm -rf dist/homemaker
	#rm -rf dist
	mkdir -p dist/homemaker/libs/site/packages
	cp -r molior/ topologist/ __init__.py dist/homemaker/
	rm -rf dist/homemaker/*/__pycache__
	rm -rf dist/homemaker/*/*/__pycache__
	mkdir -p dist/working

	cd dist/working && wget https://files.pythonhosted.org/packages/94/0b/960513ec1b582793e92dafb7915c6498d688fd619f79691916b84f2f3bee/cppyy_cling-6.25.0-py2.py3-none-manylinux2014_x86_64.whl
	cd dist/working && wget https://files.pythonhosted.org/packages/85/15/f7a4b706c6b91045ee3c865ae593ddf077a463914aadddbe803c0c11992a/cppyy-backend-1.14.5.tar.gz
	cd dist/working && wget https://files.pythonhosted.org/packages/ed/a2/75e715ec671bd491729fb208b9757239148b7efe02d801032eab30c19846/CPyCppyy-1.12.6.tar.gz
	cd dist/working && wget https://files.pythonhosted.org/packages/81/3d/cf40833ecb8f2ae7024a8aeead8d5f699c3350cbf57582f087900ca0dddf/cppyy-2.0.0.tar.gz
	cd dist/working && wget https://files.pythonhosted.org/packages/ac/dd/f6fc54a770ba0222261b33d60d9c9e01aa35d989f1cdfe892ae84e319779/ezdxf-0.16.3-cp39-cp39-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_12_x86_64.manylinux2010_x86_64.whl
	cd dist/working && wget https://files.pythonhosted.org/packages/8a/bb/488841f56197b13700afd5658fc279a2025a39e22449b7cf29864669b15d/pyparsing-2.4.7-py2.py3-none-any.whl

	# TOPOLOGIC

	# topologicPy
	cp -r ~/src/topologicPy/cpython/topologic/ dist/homemaker/libs/site/packages/
	mkdir dist/homemaker/libs/site/packages/topologic/lib
	mkdir -p dist/homemaker/libs/site/packages/topologic/include/api

	# TopologicCore (headers are already in topologicPy)
	# FIXME this is copying the installed fedora RPM
	# NOTE: renaming from .so.0 to .so
	cp /usr/lib64/libTopologicCore.so.0 dist/homemaker/libs/site/packages/topologic/lib/libTopologicCore.so

	# opencascade
	# FIXME this is copying the installed fedora RPM
	cp /usr/lib64/libTKernel.so.7 dist/homemaker/libs/site/packages/topologic/lib/
	cp /usr/lib64/libTKMath.so.7 dist/homemaker/libs/site/packages/topologic/lib/
	cp /usr/lib64/libTKG2d.so.7 dist/homemaker/libs/site/packages/topologic/lib/
	cp /usr/lib64/libTKG3d.so.7 dist/homemaker/libs/site/packages/topologic/lib/
	cp /usr/lib64/libTKGeomBase.so.7 dist/homemaker/libs/site/packages/topologic/lib/
	cp /usr/lib64/libTKBRep.so.7 dist/homemaker/libs/site/packages/topologic/lib/
	cp /usr/lib64/libTKGeomAlgo.so.7 dist/homemaker/libs/site/packages/topologic/lib/
	cp /usr/lib64/libTKTopAlgo.so.7 dist/homemaker/libs/site/packages/topologic/lib/
	cp /usr/lib64/libTKPrim.so.7 dist/homemaker/libs/site/packages/topologic/lib/
	cp /usr/lib64/libTKShHealing.so.7 dist/homemaker/libs/site/packages/topologic/lib/
	cp /usr/lib64/libTKBO.so.7 dist/homemaker/libs/site/packages/topologic/lib/
	cp /usr/lib64/libTKBool.so.7 dist/homemaker/libs/site/packages/topologic/lib/
	cp /usr/lib64/libTKFillet.so.7 dist/homemaker/libs/site/packages/topologic/lib/
	cp /usr/lib64/libTKOffset.so.7 dist/homemaker/libs/site/packages/topologic/lib/
	cp /usr/lib64/libTKMesh.so.7 dist/homemaker/libs/site/packages/topologic/lib/

        # this is actually only a small number of opencascade headers

	for FILE in BOPAlgo_Algo.hxx BOPAlgo_Builder.hxx BOPAlgo_BuilderShape.hxx BOPAlgo_CellsBuilder.hxx BOPAlgo_GlueEnum.hxx BOPAlgo_Operation.hxx BOPAlgo_Options.hxx BOPAlgo_PBuilder.hxx BOPAlgo_PPaveFiller.hxx BOPDS_PDS.hxx BRepAlgoAPI_Algo.hxx BRepAlgoAPI_BooleanOperation.hxx BRepAlgoAPI_BuilderAlgo.hxx BRepBuilderAPI_Command.hxx BRepBuilderAPI_EdgeError.hxx BRepBuilderAPI_MakeShape.hxx BRepTools_History.hxx Geom2d_Transformation.hxx GeomAbs_BSplKnotDistribution.hxx GeomAbs_Shape.hxx Geom_BoundedCurve.hxx Geom_BoundedSurface.hxx Geom_BSplineCurve.hxx Geom_BSplineSurface.hxx Geom_Curve.hxx Geom_Direction.hxx Geom_ElementarySurface.hxx Geom_Geometry.hxx Geom_Line.hxx Geom_Plane.hxx Geom_Surface.hxx Geom_Vector.hxx Geom_VectorWithMagnitude.hxx gp_Ax1.hxx gp_Ax1.lxx gp_Ax2d.hxx gp_Ax2d.lxx gp_Ax2.hxx gp_Ax2.lxx gp_Ax3.hxx gp_Ax3.lxx gp_Dir2d.hxx gp_Dir2d.lxx gp_Dir.hxx gp_Dir.lxx gp.hxx gp.lxx gp_Mat2d.hxx gp_Mat2d.lxx gp_Mat.hxx gp_Mat.lxx gp_Pnt2d.hxx gp_Pnt2d.lxx gp_Pnt.hxx gp_Pnt.lxx gp_Trsf2d.hxx gp_Trsf2d.lxx gp_TrsfForm.hxx gp_Trsf.hxx gp_Trsf.lxx gp_Vec2d.hxx gp_Vec2d.lxx gp_Vec.hxx gp_Vec.lxx gp_VectorWithNullMagnitude.hxx gp_XY.hxx gp_XY.lxx gp_XYZ.hxx gp_XYZ.lxx ; \
	do cp /usr/include/opencascade/$${FILE} dist/homemaker/libs/site/packages/topologic/include/ ; done

	for FILE in Message_AlertExtended.hxx Message_Alert.hxx Message_Gravity.hxx Message.hxx Message_Level.hxx Message_ListOfAlert.hxx Message_Messenger.hxx Message_MetricType.hxx Message_Printer.hxx Message_Report.hxx Message_SequenceOfPrinters.hxx NCollection_Array1.hxx NCollection_Array2.hxx NCollection_BaseAllocator.hxx NCollection_BaseList.hxx NCollection_BaseMap.hxx NCollection_BaseSequence.hxx NCollection_BaseVector.hxx NCollection_DataMap.hxx NCollection_DefaultHasher.hxx NCollection_DefineAlloc.hxx NCollection_DefineArray1.hxx NCollection_DefineArray2.hxx NCollection_DefineHArray1.hxx NCollection_DefineHArray2.hxx NCollection_Handle.hxx NCollection_IndexedDataMap.hxx NCollection_IndexedMap.hxx NCollection_List.hxx NCollection_ListNode.hxx NCollection_Map.hxx NCollection_Mat4.hxx NCollection_Sequence.hxx NCollection_StlIterator.hxx NCollection_TListIterator.hxx NCollection_TListNode.hxx NCollection_TypeDef.hxx NCollection_Vec2.hxx NCollection_Vec3.hxx NCollection_Vec4.hxx NCollection_Vector.hxx OSD_MemInfo.hxx Precision.hxx ; \
	do cp /usr/include/opencascade/$${FILE} dist/homemaker/libs/site/packages/topologic/include/ ; done

	for FILE in Standard_Address.hxx Standard_Assert.hxx Standard_Boolean.hxx Standard_Character.hxx Standard_ConstructionError.hxx Standard_CString.hxx Standard_DefineAlloc.hxx Standard_DefineException.hxx Standard_DimensionError.hxx Standard_DimensionMismatch.hxx Standard_DomainError.hxx Standard_Dump.hxx Standard_ErrorHandler.hxx Standard_ExtCharacter.hxx Standard_ExtString.hxx Standard_Failure.hxx Standard_Handle.hxx Standard_HandlerStatus.hxx Standard.hxx Standard_Integer.hxx Standard_IStream.hxx Standard_JmpBuf.hxx Standard_Macro.hxx Standard_math.hxx Standard_Mutex.hxx Standard_NoSuchObject.hxx Standard_OStream.hxx Standard_OutOfMemory.hxx Standard_OutOfRange.hxx Standard_PCharacter.hxx Standard_PErrorHandler.hxx Standard_PExtCharacter.hxx Standard_PrimitiveTypes.hxx Standard_ProgramError.hxx Standard_RangeError.hxx Standard_Real.hxx Standard_Size.hxx Standard_SStream.hxx Standard_Std.hxx Standard_Stream.hxx Standard_ThreadId.hxx Standard_Transient.hxx Standard_TypeDef.hxx Standard_Type.hxx Standard_TypeMismatch.hxx Standard_values.h ; \
	do cp /usr/include/opencascade/$${FILE} dist/homemaker/libs/site/packages/topologic/include/ ; done

	for FILE in TColgp_Array1OfPnt.hxx TColgp_Array2OfPnt.hxx TColgp_HArray1OfPnt.hxx TColgp_HArray2OfPnt.hxx TCollection_AsciiString.hxx TCollection_AsciiString.lxx TCollection_ExtendedString.hxx TCollection_HAsciiString.hxx TCollection_HAsciiString.lxx TCollection_HExtendedString.hxx TColStd_Array1OfInteger.hxx TColStd_Array1OfReal.hxx TColStd_Array2OfReal.hxx TColStd_HArray1OfInteger.hxx TColStd_HArray1OfReal.hxx TColStd_HArray2OfReal.hxx TColStd_MapIntegerHasher.hxx TopAbs.hxx TopAbs_Orientation.hxx TopAbs_ShapeEnum.hxx TopAbs_State.hxx TopExp_Explorer.hxx TopExp_Explorer.lxx TopExp.hxx TopExp_Stack.hxx TopLoc_ItemLocation.hxx TopLoc_Location.hxx TopLoc_Location.lxx TopLoc_SListOfItemLocation.hxx TopoDS_Builder.hxx TopoDS_Builder.lxx TopoDS_Compound.hxx TopoDS_Compound.lxx TopoDS_CompSolid.hxx TopoDS_CompSolid.lxx TopoDS_Edge.hxx TopoDS_Edge.lxx TopoDS_Face.hxx TopoDS_Face.lxx TopoDS_Iterator.hxx TopoDS_Iterator.lxx TopoDS_ListIteratorOfListOfShape.hxx TopoDS_ListOfShape.hxx TopoDS_Shape.hxx TopoDS_Shell.hxx TopoDS_Shell.lxx TopoDS_Solid.hxx TopoDS_Solid.lxx TopoDS_TCompound.hxx TopoDS_TCompound.lxx TopoDS_TCompSolid.hxx TopoDS_TCompSolid.lxx TopoDS_TShape.hxx TopoDS_TShell.hxx TopoDS_TShell.lxx TopoDS_TSolid.hxx TopoDS_TSolid.lxx TopoDS_TWire.hxx TopoDS_TWire.lxx TopoDS_Vertex.hxx TopoDS_Vertex.lxx TopoDS_Wire.hxx TopoDS_Wire.lxx TopTools_DataMapOfIntegerListOfShape.hxx TopTools_DataMapOfShapeInteger.hxx TopTools_DataMapOfShapeListOfShape.hxx TopTools_DataMapOfShapeShape.hxx TopTools_IndexedDataMapOfShapeListOfShape.hxx TopTools_IndexedMapOfShape.hxx TopTools_ListOfShape.hxx TopTools_MapOfShape.hxx TopTools_ShapeMapHasher.hxx TopTools_ShapeMapHasher.lxx ; \
	do cp /usr/include/opencascade/$${FILE} dist/homemaker/libs/site/packages/topologic/include/ ; done

	# CPPYY

	cd dist/working && unzip cppyy_cling-*.whl
	cp -r dist/working/cppyy_backend dist/homemaker/libs/site/packages/

	cd dist/working && tar -xzvf cppyy-backend-*.tar.gz
	cd dist/working/cppyy-backend-1.14.5/ && PYTHONPATH=../../homemaker/libs/site/packages python setup.py build && cp -r build/lib.*/cppyy_backend/lib/* ../../homemaker/libs/site/packages/cppyy_backend/lib/

	cd dist/working && tar -xzvf CPyCppyy-*.tar.gz
	cd dist/working/CPyCppyy-1.12.6/ && PYTHONPATH=../../homemaker/libs/site/packages python setup.py build && cp -r build/lib.*/* ../../homemaker/libs/site/packages/ && cp -r include/CPyCppyy ../../homemaker/libs/site/packages/topologic/include/api/

	cd dist/working && tar -xzvf cppyy-2.0.0.tar.gz
	cd dist/working/cppyy-2.0.0/ && PYTHONPATH=../../homemaker/libs/site/packages python setup.py build && cp -r build/lib/cppyy ../../homemaker/libs/site/packages/

	strip dist/homemaker/libs/site/packages/cppyy_backend/lib/*.so
	strip dist/homemaker/libs/site/packages/*.so

	# EZDXF

	cd dist/working && unzip ezdxf-0.16.3-*.whl
	cp -r dist/working/ezdxf dist/homemaker/libs/site/packages/

	cd dist/working && unzip pyparsing-2.4.7-*.whl
	cp dist/working/pyparsing.py dist/homemaker/libs/site/packages/

	cd dist && zip -r blender-homemaker-$(VERSION)-$(PYVERSION)-$(PLATFORM).zip ./homemaker
	#rm -rf dist/homemaker
	#rm -rf dist/working

clean:
	rm -rf dist

.PHONY: dist clean

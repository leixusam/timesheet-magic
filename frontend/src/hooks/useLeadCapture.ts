'use client';

import { LeadData } from '@/types/leadCapture';
import { useMapsLibrary } from '@vis.gl/react-google-maps';
import { useEffect, useRef, useState } from 'react';

export function useLeadCapture(initialData: LeadData) {
  const [leadData, setLeadData] = useState<LeadData>(initialData);
  const [storeNamePrediction, setStoreNamePrediction] = useState<google.maps.places.AutocompletePrediction[]>([]);
  const [storeAddressPrediction, setStoreAddressPrediction] = useState<google.maps.places.AutocompletePrediction[]>([]);
  const [errors, setErrors] = useState<Partial<Record<keyof LeadData, string>>>({});
  
  const storeNameInputRef = useRef<HTMLInputElement>(null);
  const storeAddressInputRef = useRef<HTMLInputElement>(null);

  const places = useMapsLibrary('places');
  const [autocompleteService, setAutocompleteService] = useState<google.maps.places.AutocompleteService | null>(null);
  const [placesService, setPlacesService] = useState<google.maps.places.PlacesService | null>(null);

  useEffect(() => {
    if (places) {
      setAutocompleteService(new places.AutocompleteService());
      const dummyMapDiv = document.createElement('div'); 
      setPlacesService(new places.PlacesService(dummyMapDiv));
    }
  }, [places]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setLeadData((prevData) => ({
      ...prevData,
      [name]: value,
    }));

    if (autocompleteService) {
      if (name === 'storeName' && value.length > 0) {
        autocompleteService.getPlacePredictions(
          { input: value, types: ['establishment'] },
          (predictions, status) => {
            if (status === google.maps.places.PlacesServiceStatus.OK && predictions) {
              setStoreNamePrediction(predictions);
            } else {
              setStoreNamePrediction([]);
            }
          }
        );
      }
      if (name === 'storeAddress' && value.length > 0) {
         autocompleteService.getPlacePredictions(
          { input: value, types: ['address'] },
          (predictions, status) => {
            if (status === google.maps.places.PlacesServiceStatus.OK && predictions) {
              setStoreAddressPrediction(predictions);
            } else {
              setStoreAddressPrediction([]);
            }
          }
        );
      }
    }
  };
  
  const handlePredictionSelect = (field: 'storeName' | 'storeAddress', prediction: google.maps.places.AutocompletePrediction) => {
    console.log(`handlePredictionSelect called for field: ${field}`, prediction);
    if (!placesService || !prediction.place_id) {
      console.error('PlacesService or prediction.place_id is missing', { placesService, place_id: prediction?.place_id });
      setErrors(prev => ({...prev, [field]: "Could not fetch details for this selection."}));
      return;
    }

    placesService.getDetails({ placeId: prediction.place_id }, (place, status) => {
      console.log('placesService.getDetails callback status:', status);
      if (status === google.maps.places.PlacesServiceStatus.OK && place) {
        console.log('Place details received:', place);
        let newStoreName = leadData.storeName;
        let newStoreAddress = leadData.storeAddress;
        // Clear previous errors for these fields on successful fetch
        setErrors(prev => ({...prev, storeName: undefined, storeAddress: undefined}));

        if (field === 'storeName') {
            newStoreName = place.name || prediction.description || leadData.storeName;
            newStoreAddress = place.formatted_address || leadData.storeAddress; // Populate address when store name is selected
            console.log(`Updating for storeName: Name: ${newStoreName}, Address: ${newStoreAddress}`);
            setLeadData(prev => ({ 
                ...prev, 
                storeName: newStoreName,
                storeAddress: newStoreAddress 
            }));
            setStoreNamePrediction([]);
            if (storeNameInputRef.current) storeNameInputRef.current.focus();
        } else if (field === 'storeAddress') {
            newStoreAddress = place.formatted_address || prediction.description || leadData.storeAddress;
            console.log(`Updating for storeAddress: Address: ${newStoreAddress}`);
            // Optionally, if an address is picked, you might want to update the storeName if it's not already set or clear it
            // For now, just updating address based on selection
            setLeadData(prev => ({ 
                ...prev, 
                storeAddress: newStoreAddress 
            }));
            setStoreAddressPrediction([]);
            if (storeAddressInputRef.current) storeAddressInputRef.current.focus();
        }
      } else {
        console.error('Error fetching place details or place is null:', status, place);
        setErrors(prev => ({...prev, [field]: "Error fetching place details."}));
      }
    });
  };

  const validateForm = () => {
    const newErrors: Partial<Record<keyof LeadData, string>> = {};
    if (!leadData.managerName) newErrors.managerName = 'Manager Name is required.';
    if (!leadData.managerEmail) newErrors.managerEmail = 'Manager Email is required.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(leadData.managerEmail)) newErrors.managerEmail = 'Manager Email is invalid.';
    if (!leadData.managerPhone) newErrors.managerPhone = 'Manager Phone is required.';
    if (!leadData.storeName) newErrors.storeName = 'Store Name is required.';
    if (!leadData.storeAddress) newErrors.storeAddress = 'Store Physical Address is required.';
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  return {
    leadData,
    handleInputChange,
    storeNameInputRef,
    storeAddressInputRef,
    storeNamePrediction,
    setStoreNamePrediction,
    storeAddressPrediction,
    setStoreAddressPrediction,
    handlePredictionSelect,
    setLeadData,
    errors,
    validateForm,
  };
} 
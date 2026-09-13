
package de.mogwailabs.BSidesRMIService;

import java.rmi.Remote;
import java.rmi.RemoteException;

// ok:server-dangerous-object-deserialization
public interface IBSidesServiceOK extends Remote {
   boolean registerTicket(String ticketID) throws RemoteException;
   void vistTalk(String talkID) throws RemoteException;
   void poke(Integer attende) throws RemoteException;
}

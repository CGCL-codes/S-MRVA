
package de.mogwailabs.BSidesRMIService;

import java.rmi.Remote;
import java.rmi.RemoteException;

// ruleid:server-dangerous-class-deserialization
public interface IBSidesService extends Remote {
   boolean registerTicket(String ticketID) throws RemoteException;
   void vistTalk(String talkname) throws RemoteException;
   void poke(Attendee attende) throws RemoteException;
}
